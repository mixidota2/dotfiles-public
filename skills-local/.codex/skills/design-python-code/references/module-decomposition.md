# Module分割と統合

## Flat packageを維持する条件

次の状態なら、package直下に複数の`.py`が並んでいても問題にしない。

- package全体が一つの凝集した能力を表す。
- file名から責務と主要なcallerを推測できる。
- public APIが安定し、内部file配置がconsumerへ露出していない。
- 代表変更が少数の関連fileへ局所化する。
- 状態、不変条件、権限のownerが衝突していない。
- directoryを追加しても依存や理解が明確にならない。

file数だけで閾値を決めない。

## 分割を検討する兆候

- `services.py`、`models.py`、`utils.py`が複数の無関係な用語・変更理由を持つ。
- 同じprefixのfile群が固有の状態やadapterを共有する。
- 一機能の変更でpackage全体の多数fileを編集する。
- import cycle、条件分岐、共有mutable stateが増えている。
- public consumerが内部fileを直接importしている。
- 一部だけをtest、replace、deleteすることが難しい。

## 分割単位

次の順で最小単位を選ぶ。

1. function内の責務を整理する。
2. classまたはoperation単位のmoduleへ分ける。
3. 同じ意味・状態・公開面を持つmodule群をsubpackageへ昇格する。
4. package間契約が必要な場合だけ公開facadeまたはProtocolを置く。

operation-centered moduleは、意味ある一操作とそのinput/resultをまとめる場合に有効である。各functionを一fileにする規則にはしない。

## God fileの扱い

`services.py`等を機械的に小分けせず、各要素について次を記録する。

```text
- 現在のsymbol
- 業務上または技術上の意味
- caller
- 読み書きする状態
- 依存先
- 変更理由
- keep / rename / split / merge / move
```

異なる名前でも同時に一つの不変条件を守るsymbolは近くへ残す。同じ名前空間でもownerが異なるものは分ける。

## 命名

- `utils.py`、`common.py`、`helpers.py`を新しい責務の逃げ場にしない。
- package名は現在の業務用語または明確なtechnical capabilityを使う。
- `manager`、`service`、`processor`のような広い語は、責務を具体化できない場合に避ける。
- private implementationには必要に応じて先頭`_`を付け、公開面と区別する。

提案では現行treeと提案treeを示し、移動ごとに変更局所性がどう改善するかを説明する。
