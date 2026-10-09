# Domain modeling

業務ルール、状態、許可・禁止される操作が主要な設計判断に含まれる場合だけ適用する。

## 最初に確認するもの

- 現場で使われる用語とcontext
- entityを識別するkeyとlifecycle
- 値の妥当性と単位
- 状態遷移と禁止遷移
- 操作前後で必ず成立する不変条件
- 誰が状態変更を決定できるか
- 正として保存されるsource

## Ownerを区別する

- `semantic owner`: 値や状態の意味を定義する場所
- `invariant owner`: 不正状態を防ぐ場所
- `state authority`: 状態変更を決定できる場所
- `source of truth`: 正として保存されるsystemまたはdata
- `writer`: 実際に書き込む経路
- `reader`: 読み取る経路

これらを同一と仮定しない。ただし、理由なく複数moduleへ分散させない。

## Modelを作る判断

- identityとlifecycleが重要ならentityを検討する。
- 単位、検証、比較規則を持つ値ならvalue objectを検討する。
- 値の集合に意味がなく単なるtransportならdataclassやmappingで十分な場合がある。
- `NewType`はstaticな取り違え防止には使えるが、runtime validationやbehaviorは提供しない。
- primitiveをclass化すること自体を目的にしない。

状態変更は意味あるoperationへ閉じ込める。

```python
order.cancel(now=clock.now())
```

各所から次のように直接変更させない。

```python
order.status = OrderStatus.CANCELLED
```

## Alternate writerを探す

通常のapplication codeだけでなく、次を確認する。

- ORM hook、bulk update、raw SQL
- serializer/deserializer
- fixture、factory、seed
- admin画面、maintenance script、migration
- scheduled job、event consumer、retry処理
- cache復元、snapshot import

不正状態を作れる経路が残るなら、directory構造だけを整えても完了ではない。

## Failure後の状態

外部side effectを伴うoperationでは、成功・失敗だけでなくtimeout、部分成功、結果不明、重複実行後の状態を定義する。domainがvendor例外を直接知る必要があるかは`interface-boundaries.md`で判断する。
