# Interfaceと外部依存の境界

## Contractをconsumerから定義する

interfaceを作る前に次を確認する。

- consumerは誰か。
- 何を達成するための操作か。
- input、result、failure、side effectは何か。
- deadline、retry、idempotency、順序保証は必要か。
- vendor固有の型・例外・lifecycleを漏らすと何が困るか。

providerのAPI全体を写したinterfaceではなく、consumerが必要とする最小の意味ある操作を定義する。

## Protocolを作る条件

`Protocol`は次の場合に候補にする。

- 複数実装または具体的な交換シナリオがある。
- adapterの契約testを共有したい。
- 外部SDKやstorage implementationをdomain/use caseから隔離したい。
- failure注入を含むtest doubleが重要な契約を表す。

一実装だけで境界の価値もない場合、具体classまたはcallableを直接注入する方が単純である。

## 公開API

- package consumerが使うsymbolを`__init__.py`等のfacadeから公開する。
- consumerに内部file pathを記憶させない。
- `__all__`は公開面を明示する必要がある場合に使う。
- internal moduleのrenameやsplitがconsumerへ波及しないことを変更シナリオで確認する。
- framework handlerはinput/output変換を担当し、domain decisionを持たない。

## Adapterとcomposition root

- port/contractはconsumer側の意味で命名する。
- adapterはDB、HTTP、SDKの型と例外を意味あるresult/failureへ変換する。
- composition rootで設定、credential、concrete adapter、use caseを組み立てる。
- domain moduleやhandler内で環境変数を直接読む構造を増やさない。既存の設定注入方式を再利用する。

## Failure contract

外部呼び出しでは少なくとも次を区別する必要性を検討する。

- 明確な拒否またはnot found
- 一時的失敗
- timeoutまたは結果不明
- 部分成功
- retryによるduplicate

全例外を一つに潰さず、consumerが実際に異なる判断をするfailureだけを区別する。例外class階層の数を品質指標にしない。

## 過剰抽象化の兆候

- `AbstractX`、`BaseX`、`XFactory`、`XStrategy`が同じ一実装を包むだけである。
- callerの条件分岐が減らず、型だけ増えている。
- concrete implementationを知るmoduleがcomposition root以外にも散っている。
- interface変更のたびに全実装と全callerを同時変更する。
- contract testがなく、実装固有behaviorを抽象名で隠している。
