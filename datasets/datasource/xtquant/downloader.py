import os
import pandas as pd
from datetime import datetime
from loguru import logger
from ..base_downloader import BaseDownloader
from xtquant import xtdata
import json

class XtquantDownloader(BaseDownloader):
    """Xtquant新版数据下载器"""

    def __init__(
        self,
        config_path: str = None,
        provider: str = 'xtquant',
        start_date: str = None,
        end_date: str = None,
        convert: bool = False,
        interval: str = '1d',
        stock_codes: list = None
    ):
        super().__init__(
            config_path=config_path,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
            convert=convert,
            interval=interval,
            stock_codes=stock_codes
        )
        if self.stock_codes is None:
            stock_df = self.download_stock_list()
            self.stock_codes = stock_df['code'].tolist()
        self.trade_dates = self.get_trade_dates(self.start_date, self.end_date)
        self.all_years = set(str(y) for y in range(int(self.start_date[:4]), int(self.end_date[:4]) + 1))

    def download_stock_list(self) -> pd.DataFrame:
        logger.info('开始下载股票池列表...')
        stock_list = xtdata.get_stock_list('A')
        stock_df = pd.DataFrame(stock_list, columns=['code'])
        logger.info(f'下载股票列表{len(stock_df)}支')
        if not stock_df.empty:
            save_path = os.path.join(self.config['data_path'], 'stock_list')
            os.makedirs(save_path, exist_ok=True)
            file_path = os.path.join(save_path, f'stock_list_{datetime.now().strftime("%Y%m%d")}.csv')
            metadata = {
                'download_date': datetime.now().isoformat(),
                'record_count': len(stock_df),
                'fields': list(stock_df.columns)
            }
            self._save_with_metadata(stock_df, file_path, metadata)
            logger.info(f'股票列表已保存至: {file_path}')
        return stock_df

    def get_trade_dates(self, start_date: str, end_date: str) -> set:
        from datetime import datetime
        def ms_to_date(ms):
            return datetime.fromtimestamp(ms / 1000).strftime('%Y-%m-%d')
        start = start_date.replace('-', '')
        end = end_date.replace('-', '')
        sse_dates = set(ms_to_date(ms) for ms in xtdata.get_trading_dates('SH', start_time=start, end_time=end, count=-1))
        szse_dates = set(ms_to_date(ms) for ms in xtdata.get_trading_dates('SZ', start_time=start, end_time=end, count=-1))
        return sse_dates | szse_dates

    def download_daily_data(self, stock_code: str) -> pd.DataFrame:
        fields = self.config.get('fields', {}).get('daily', None)
        save_path = os.path.join(self.config.get('data_path', '../data/raw/xtquant'), 'daily', stock_code)
        file_path = os.path.join(save_path, f'{stock_code}_daily.csv')
        trade_dates = self.trade_dates

        if os.path.exists(file_path):
            df_local = pd.read_csv(file_path)
            if df_local.empty or 'date' not in df_local.columns:
                df_local = pd.DataFrame()
        else:
            df_local = pd.DataFrame()

        def get_local_dates(df):
            if df is None or df.empty or 'date' not in df.columns:
                return set()
            return set(pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d'))

        def split_into_ranges(dates):
            if not dates:
                return []
            from datetime import datetime, timedelta
            dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
            dates.sort()
            ranges = []
            start = dates[0]
            end = dates[0]
            for d in dates[1:]:
                if (d - end).days == 1:
                    end = d
                else:
                    ranges.append((start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))
                    start = end = d
            ranges.append((start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))
            return ranges

        def download_missing(rng):
            # 确保传递给xtquant API的日期为YYYYMMDD
            start_api = rng[0].replace('-', '')
            end_api = rng[1].replace('-', '')
            xtdata.download_history_data2(
                stock_code,
                period='1d',
                start_time=start_api,
                end_time=end_api,
                incrementally=True
            )
            df = xtdata.get_market_data_ex([], [stock_code], period='1d', start_time=start_api, end_time=end_api, count=-1)
            if isinstance(df, dict) and stock_code in df:
                df = df[stock_code]
            if isinstance(df, pd.DataFrame):
                if 'datetime' in df.columns:
                    df.rename(columns={'datetime': 'date'}, inplace=True)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                # 字段筛选：只保留fields中指定的字段（含'date'）
                if fields is not None:
                    keep_cols = ['date'] + [f for f in fields.split(',') if f.strip() and f != 'date']
                    df = df[[col for col in keep_cols if col in df.columns]]
            return df

        def merge_dfs(dfs):
            df_new = pd.concat([df for df in dfs if df is not None and not df.empty], ignore_index=True)
            if 'date' in df_new.columns:
                df_new['date'] = pd.to_datetime(df_new['date']).dt.strftime('%Y-%m-%d')
                df_new = df_new.drop_duplicates(subset=['date']).sort_values('date')
            else:
                df_new = df_new.drop_duplicates().sort_index()
            return df_new

        df_new = self.incremental_update(
            df_local,
            trade_dates,
            get_local_dates,
            download_missing,
            merge_dfs,
            split_ranges_fn=split_into_ranges
        )

        if not df_new.empty:
            os.makedirs(save_path, exist_ok=True)
            metadata = {
                'stock_code': stock_code,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'download_date': datetime.now().isoformat(),
                'record_count': len(df_new),
                'fields': list(df_new.columns)
            }
            self._save_with_metadata(df_new, file_path, metadata)
            return df_new
        else:
            return df_local

    def download_dividend_data(self, stock_code: str) -> pd.DataFrame:
        save_path = os.path.join(self.config.get('data_path', '../data/raw/xtquant'), 'dividend', stock_code)
        file_path = os.path.join(save_path, f'{stock_code}_dividend.csv')
        all_years = self.all_years

        if os.path.exists(file_path):
            df_local = pd.read_csv(file_path)
            if df_local.empty:
                df_local = pd.DataFrame()
        else:
            df_local = pd.DataFrame()

        def get_local_years(df):
            if df is None or df.empty:
                return set()
            if 'year' in df.columns:
                return set(df['year'].astype(str))
            elif 'dividend_year' in df.columns:
                return set(df['dividend_year'].astype(str))
            elif 'report_date' in df.columns:
                return set(df['report_date'].astype(str).str[:4])
            else:
                return set()

        def download_missing_year(rng):
            year = rng[0]
            start_api = f"{year}-01-01".replace('-', '')
            end_api = f"{year}-12-31".replace('-', '')
            if hasattr(xtdata, 'get_dividend'):
                df = xtdata.get_dividend(stock_code, start_api, end_api)
            else:
                df = pd.DataFrame()
            if isinstance(df, pd.DataFrame):
                if 'dividend_year' in df.columns:
                    df['year'] = df['dividend_year']
                elif 'year' not in df.columns and 'report_date' in df.columns:
                    df['year'] = df['report_date'].astype(str).str[:4]
            return df

        def merge_dfs(dfs):
            df_new = pd.concat([df for df in dfs if df is not None and not df.empty], ignore_index=True)
            if 'year' in df_new.columns:
                df_new = df_new.drop_duplicates().sort_values('year')
            else:
                df_new = df_new.drop_duplicates().sort_index()
            return df_new

        df_new = self.incremental_update(
            df_local,
            all_years,
            get_local_years,
            download_missing_year,
            merge_dfs
        )

        if not df_new.empty:
            os.makedirs(save_path, exist_ok=True)
            metadata = {
                'stock_code': stock_code,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'download_date': datetime.now().isoformat(),
                'record_count': len(df_new),
                'fields': list(df_new.columns)
            }
            self._save_with_metadata(df_new, file_path, metadata)
            self.update_status(stock_code, 'dividend', {
                'status': 'done',
                'years': list(self.all_years),
                'has_dividend': True,
                'last_update': datetime.now().strftime('%Y-%m-%d'),
            })
            return df_new
        else:
            self.update_status(stock_code, 'dividend', {
                'status': 'done',
                'years': list(self.all_years),
                'has_dividend': False,
                'last_update': datetime.now().strftime('%Y-%m-%d'),
            })
            return df_local 