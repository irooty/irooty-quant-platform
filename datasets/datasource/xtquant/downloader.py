# 统一路径操作工具，避免直接用os.path
import utils.path_utils as path_utils
import pandas as pd
from datetime import datetime
from loguru import logger
from ..base_downloader import BaseDownloader
from xtquant import xtdata
import json

register = BaseDownloader.download_dispatcher.register

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
        # 统一所有股票代码格式为xtquant标准格式
        if self.stock_codes is None:
            stock_df = self.download_stock_list()
            self.stock_codes = [self.to_xtquant_code(code) for code in stock_df['code'].tolist()]
        else:
            self.stock_codes = [self.to_xtquant_code(code) for code in self.stock_codes]
        self.trade_dates = self.get_trade_dates(self.start_date, self.end_date)
        self.all_years = set(str(y) for y in range(int(self.start_date[:4]), int(self.end_date[:4]) + 1))

    @staticmethod
    def to_xtquant_code(code):
        """
        将各种常见股票代码格式（如 'sh600000', '600000.SH', '600000.sh', 'SH.600000', 'sh.600000', '600000' 等）
        统一转换为 xtquant 标准格式 '000000.SH' 或 '000000.SZ'。
        """
        code = code.replace(' ', '').replace('-', '').replace('_', '').upper()
        if '.' in code:
            parts = code.split('.')
            if len(parts[0]) == 2 and len(parts[1]) == 6:  # sh.600000
                return f"{parts[1]}.{parts[0].upper()}"
            elif len(parts[1]) == 2 and len(parts[0]) == 6:  # 600000.SH
                return f"{parts[0]}.{parts[1].upper()}"
            else:
                # 其它情况，尽量容错
                return f"{parts[-1].zfill(6)}.{parts[0][:2].upper()}"
        elif code.startswith('SH') or code.startswith('SZ'):
            return f"{code[2:].zfill(6)}.{code[:2]}"
        elif code.startswith('SZ') or code.startswith('SH'):
            return f"{code[2:].zfill(6)}.{code[:2]}"
        else:
            # 默认上证
            return f"{code.zfill(6)}.SH"

    def download_stock_list(self) -> pd.DataFrame:
        logger.info('开始下载股票池列表...')
        stock_list = xtdata.get_stock_list('A')
        stock_df = pd.DataFrame(stock_list, columns=['code'])
        logger.info(f'下载股票列表{len(stock_df)}支')
        if not stock_df.empty:
            save_path = path_utils.safe_join(self.config['data_path'], 'stock_list')
            path_utils.safe_makedirs(save_path, exist_ok=True)
            file_path = path_utils.safe_join(save_path, f'stock_list_{datetime.now().strftime("%Y%m%d")}.csv')
            metadata = {
                'download_date': datetime.now().isoformat(),
                'record_count': len(stock_df),
                'fields': list(stock_df.columns)
            }
            self._save_with_metadata(stock_df, file_path, metadata)
            logger.info(f'股票列表已保存至: {file_path}')
        return stock_df

    @staticmethod
    def get_trade_dates(start_date: str, end_date: str) -> set:
        from datetime import datetime
        def ms_to_date(ms):
            return datetime.fromtimestamp(ms / 1000).strftime('%Y-%m-%d')
        start = start_date.replace('-', '')
        end = end_date.replace('-', '')
        sse_dates = set(ms_to_date(ms) for ms in xtdata.get_trading_dates('SH', start_time=start, end_time=end, count=-1))
        szse_dates = set(ms_to_date(ms) for ms in xtdata.get_trading_dates('SZ', start_time=start, end_time=end, count=-1))
        return sse_dates | szse_dates

    @register('1d')
    def download_daily_data(self, stock_code: str) -> pd.DataFrame:
        stock_code = self.to_xtquant_code(stock_code)
        fields = self.config.get('fields', {}).get('daily', None)
        save_path = path_utils.safe_join(self.config.get('data_path', '../data/raw/xtquant'), 'daily', stock_code)
        file_path = path_utils.safe_join(save_path, f'{stock_code}_daily.csv')
        trade_dates = self.trade_dates

        if path_utils.safe_exists(file_path):
            df_local = pd.read_csv(file_path)
            if df_local.empty or 'date' not in df_local.columns:
                df_local = pd.DataFrame()
        else:
            df_local = pd.DataFrame()

        def get_local_dates(df):
            if df is None or df.empty or 'date' not in df.columns:
                return set()
            return set(pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d'))

        def download_missing(rng):
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
                if 'time' in df.columns:
                    df.rename(columns={'time': 'date'}, inplace=True)
                df['date'] = df['date'].astype(str)
                if fields is not None:
                    if isinstance(fields, str):
                        field_list = [f for f in fields.split(',') if f.strip() and f != 'date']
                    elif isinstance(fields, list):
                        field_list = [f for f in fields if f.strip() and f != 'date']
                    else:
                        field_list = []
                    keep_cols = ['date'] + field_list
                    df = df[[col for col in keep_cols if col in df.columns]]
            return df

        def merge_dfs(dfs):
            df_new = pd.concat([df for df in dfs if df is not None and not df.empty], ignore_index=True)
            if 'date' in df_new.columns:
                sample = df_new['date'].iloc[0] if not df_new.empty else ''
                if isinstance(sample, (int, float)) or (isinstance(sample, str) and sample.isdigit() and len(sample) > 8):
                    df_new['date'] = pd.to_datetime(df_new['date'].astype(float), unit='ms').dt.strftime('%Y-%m-%d')
                elif isinstance(sample, str) and len(sample) == 8 and sample.isdigit():
                    df_new['date'] = pd.to_datetime(df_new['date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')
                else:
                    df_new['date'] = pd.to_datetime(df_new['date']).dt.strftime('%Y-%m-%d')
                df_new = df_new.drop_duplicates(subset=['date']).sort_values('date')
            else:
                df_new = df_new.drop_duplicates().sort_index()
            return df_new

        def metadata_fn(df_new):
            return {
                'stock_code': stock_code,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'download_date': datetime.now().isoformat(),
                'record_count': len(df_new),
                'fields': list(df_new.columns)
            }

        df_new = self.incremental_download(
            stock_code=stock_code,
            target_set=trade_dates,
            get_local_set_fn=get_local_dates,
            download_missing_fn=download_missing,
            merge_fn=merge_dfs,
            save_path=save_path,
            file_path=file_path,
            metadata_fn=metadata_fn,
            status_type='1d'
        )
        return df_new

    @register('dividend')
    def download_dividend_data(self, stock_code: str) -> pd.DataFrame:
        stock_code = self.to_xtquant_code(stock_code)
        save_path = path_utils.safe_join(self.config.get('data_path', '../data/raw/xtquant'), 'dividend', stock_code)
        file_path = path_utils.safe_join(save_path, f'{stock_code}_dividend.csv')
        all_years = self.all_years

        if path_utils.safe_exists(file_path):
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

        def metadata_fn(df_new):
            return {
                'stock_code': stock_code,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'download_date': datetime.now().isoformat(),
                'record_count': len(df_new),
                'fields': list(df_new.columns)
            }

        df_new = self.incremental_download(
            stock_code=stock_code,
            target_set=all_years,
            get_local_set_fn=get_local_years,
            download_missing_fn=download_missing_year,
            merge_fn=merge_dfs,
            save_path=save_path,
            file_path=file_path,
            metadata_fn=metadata_fn,
            status_type='dividend'
        )
        return df_new 