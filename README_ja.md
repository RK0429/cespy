# cespy

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)

spicelibとPyLTSpiceの機能を統合した、SPICE回路シミュレータを自動化するための統一されたPythonツールキットです。cespyは、複数のSPICEエンジンにわたる回路図編集、シミュレーション実行、結果解析、高度な回路解析を包括的にサポートします。

## 機能

### 🔧 **マルチエンジンサポート**

- **LTSpice** - ヘッドレス実行による完全な自動化サポート
- **NGSpice** - オープンソースSPICEシミュレータの統合
- **QSpice** - 次世代Qorvoシミュレータのサポート
- **Xyce** - Sandiaの並列SPICEシミュレータ統合

### 📝 **回路図＆ネットリスト編集**

- LTSpice `.asc` 回路図をプログラムで変更
- GUIなしでQSpice `.qsch` ファイルを編集
- 高レベルAPIでSPICEネットリストを操作
- 階層回路とサブサーキットのサポート
- パラメータスイープとコンポーネント値の更新

### 📊 **シミュレーション＆解析**

- **モンテカルロ解析** - コンポーネント公差を考慮した統計的回路解析
- **ワーストケース解析** - 極端な動作条件の探索
- **感度解析** - 重要なコンポーネントの特定
- **公差偏差** - コンポーネント変動の影響を解析
- **故障モード解析** - コンポーネント故障時の回路動作評価
- 並列実行によるバッチシミュレーションサポート

### 📈 **データ処理**

- すべてのサポートされたシミュレータからバイナリ `.raw` 波形ファイルを解析
- `.log` ファイルから測定データを抽出
- `.meas` ステートメントとステップ情報を処理
- スプレッドシート解析用にデータをエクスポート
- 組み込みのプロット機能

### 🌐 **分散コンピューティング**

- リモートシミュレーション用のクライアント・サーバーアーキテクチャ
- 強力なリモートマシンでシミュレーションを実行
- 並列ジョブ実行と結果取得

### 🛠️ **コマンドラインツール**

- `cespy-asc-to-qsch` - LTSpice回路図をQSpice形式に変換
- `cespy-run-server` - シミュレーションサーバーを起動
- `cespy-sim-client` - リモートシミュレーションサーバーに接続
- `cespy-ltsteps` - スプレッドシートインポート用にログファイルを処理
- `cespy-rawplot` - rawファイルから波形をプロット
- `cespy-histogram` - 測定データからヒストグラムを作成
- `cespy-raw-convert` - rawファイル形式間で変換

### 🚀 **強化されたコア機能**

- **パフォーマンス監視** - 組み込みのプロファイリングと最適化ツール
- **API一貫性** - 互換性ラッパーとパラメータ検証
- **プラットフォーム管理** - クロスプラットフォームシミュレータ検出と設定
- **高度な可視化** - 統合されたプロットと解析の可視化

## インストール

pipでインストール：

```bash
pip install cespy
```

Poetryでインストール：

```bash
poetry add cespy
```

開発用インストール：

```bash
git clone https://github.com/RK0429/cespy.git
cd cespy
poetry install
```

## クイックスタート

### 基本的なシミュレーション

```python
from cespy import simulate

# 高レベルAPIを使用してシンプルなシミュレーションを実行
result = simulate("circuit.asc", engine="ltspice")

# simulate関数がすべてを処理します：
# - シミュレータ実行ファイルを検出
# - シミュレーションを実行
# - 結果を含むSimRunnerオブジェクトを返す
```

### 高度な使用方法

```python
from cespy import LTspice, SpiceEditor, RawRead

# ネットリストをプログラムで編集
netlist = SpiceEditor("circuit.net")
netlist['R1'].value = 10000  # R1を10kに変更
netlist['C1'].value = 1e-9   # C1を1nFに変更
netlist.set_parameters(TEMP=27, VDD=3.3)
netlist.add_instruction(".step param R1 1k 10k 1k")

# 特定のシミュレータでシミュレーションを実行
sim = LTspice()
sim.run(netlist)

# 結果を解析
raw = RawRead("circuit.raw")
time = raw.get_trace("time")
vout = raw.get_trace("V(out)")

# 結果をプロット
import matplotlib.pyplot as plt
plt.plot(time.get_wave(), vout.get_wave())
plt.xlabel("時間 (s)")
plt.ylabel("Vout (V)")
plt.show()
```

### モンテカルロ解析

```python
from cespy.sim.toolkit import MonteCarloAnalysis
from cespy import AscEditor

# 公差を含む回路をセットアップ
circuit = AscEditor("filter.asc")
mc = MonteCarloAnalysis(circuit, num_runs=1000)

# コンポーネント公差を定義
mc.set_tolerance("R1", 0.05)  # 5%公差
mc.set_tolerance("C1", 0.10)  # 10%公差

# 解析を実行
mc.run()

# 結果を取得
results = mc.get_results()
```

### リモートシミュレーション

```python
from cespy.client_server import SimClient

# リモートシミュレーションサーバーに接続
client = SimClient("http://192.168.1.100", port=9000)

# シミュレーションジョブを送信
job_id = client.run("large_circuit.net")

# 完了時に結果を取得
for completed_job in client:
    results = client.get_runno_data(completed_job)
    print(f"シミュレーション {completed_job} 完了: {results}")
```

## ドキュメント

完全なドキュメントは[プロジェクトリポジトリ](https://github.com/RK0429/cespy)で利用可能です。

### 主要モジュール

- **`cespy.core`** - パターン、パフォーマンス、プラットフォーム管理のためのコアユーティリティ
- **`cespy.editor`** - 回路図とネットリスト編集ツール
- **`cespy.simulators`** - シミュレータ固有の実装
- **`cespy.sim`** - シミュレーション実行と管理
- **`cespy.sim.toolkit`** - 高度な解析ツール
- **`cespy.raw`** - Raw波形ファイル処理
- **`cespy.log`** - ログファイル解析ユーティリティ
- **`cespy.client_server`** - 分散シミュレーションサポート

## サンプル

`examples/` ディレクトリに包括的なサンプルがあります：

- `01_basic_simulation.py` - すべてのサポートされたシミュレータの入門
- `02_circuit_editing.py` - プログラムによる回路図とネットリスト操作
- `03_analysis_toolkit.py` - モンテカルロ、ワーストケース、感度解析
- `04_data_processing.py` - 効率的なデータ処理と可視化
- `05_batch_distributed.py` - 並列および分散シミュレーションワークフロー
- `06_platform_integration.py` - クロスプラットフォーム互換性と自動検出

すべてのサンプルを実行：`python examples/run_all_examples.py`

## spicelib/PyLTSpiceからの移行

spicelibまたはPyLTSpiceから移行する場合：

- spicelibユーザー：ほとんどのAPIは同じままで、インポートを `spicelib` から `cespy` に更新するだけです
- PyLTSpiceユーザー：`PyLTSpice.LTSpiceSimulation` を `cespy.simulate()` または `cespy.LTspice` に置き換えます

詳細な手順については、[移行ガイド](docs/migration_guide.md)を参照してください。

## 開発

開発用インストールとテスト：

```bash
# 開発依存関係を含めてインストール
poetry install

# テストを実行
poetry run pytest

# コード品質チェック
poetry run black src/ tests/      # コードフォーマット
poetry run flake8 src/ tests/     # リントチェック
poetry run mypy src/              # 型チェック
poetry run pylint src/            # 追加のリンティング

# ドキュメントをビルド
cd docs && make html
```

## 貢献

貢献を歓迎します！プルリクエストを自由に送信してください。大きな変更については、まず変更したい内容を議論するためにissueを開いてください。

## ライセンス

このプロジェクトはGNU General Public License v3.0でライセンスされています - 詳細は[LICENSE](LICENSE)ファイルをご覧ください。

## 著者

- Nuno Brum（オリジナルのspicelib/PyLTSpice作者）
- Ryota Kobayashi（cespy統合とメンテナンス）

## 謝辞

cespyは以下の統合バージョンです：

- **spicelib** - 包括的なSPICE自動化ライブラリ
- **PyLTSpice** - 専門的なLTSpice自動化ツール

両プロジェクトは元々Nuno Brumによって作成されました。
