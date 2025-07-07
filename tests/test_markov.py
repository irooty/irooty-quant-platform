import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from hmmlearn.hmm import GaussianHMM
import warnings
warnings.filterwarnings("ignore")

# 读取本地中证1000数据
df = pd.read_csv('data/000852.csv')

# 转换时间格式 & 按时间升序排序
df['date'] = pd.to_datetime(df['date'])
df.sort_values('date', inplace=True)
df.set_index('date', inplace=True)

# 只保留 close 和 volume 字段
df = df[['close', 'volume']].copy()
df.rename(columns={'close': 'Close', 'volume': 'Volume'}, inplace=True)

# 计算 log return 和波动率
df['log_return'] = np.log(df['Close'] / df['Close'].shift(1))
df['volatility'] = df['log_return'].rolling(window=10).std()

# 技术指标
df['momentum_5d'] = df['Close'] / df['Close'].shift(5) - 1
df['zscore_price_20d'] = (df['Close'] - df['Close'].rolling(20).mean()) / df['Close'].rolling(20).std()

up = df['log_return'].clip(lower=0).rolling(14).mean()
down = -df['log_return'].clip(upper=0).rolling(14).mean()
df['rsi_14'] = 100 - 100 / (1 + up / down)

df.dropna(inplace=True)

print(f"数据时间范围: {df.index.min()} 到 {df.index.max()}")
print(f"总数据点: {len(df)}")

# HMM建模
X = df[['log_return', 'volatility', 'momentum_5d', 'zscore_price_20d', 'rsi_14']].values
model = GaussianHMM(n_components=3, covariance_type="full", n_iter=1000, random_state=42)
model.fit(X)
df['state'] = model.predict(X)

# 统计各状态信息
print("\n=== 状态统计 ===")
for state in range(model.n_components):
    state_data = df[df['state'] == state]
    print(f"状态 {state}:")
    print(f"  数量: {len(state_data)}")
    print(f"  占比: {len(state_data)/len(df)*100:.2f}%")
    print(f"  平均收益率: {state_data['log_return'].mean():.4f}")
    print(f"  平均波动率: {state_data['volatility'].mean():.4f}")
    print(f"  平均价格: {state_data['Close'].mean():.2f}")

# 可视化
plt.figure(figsize=(14, 6))
colors = ['red', 'green', 'blue']
for state in range(model.n_components):
    idx = df[df['state'] == state].index
    plt.plot(idx, df.loc[idx, 'Close'], '.', label=f'State {state}', color=colors[state], markersize=2)

plt.title('中证1000 Hidden Markov 市场状态')
plt.xlabel('Date')
plt.ylabel('Close Price')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
