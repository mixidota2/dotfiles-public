# Pythonでの実現方法

設計判断をPythonへ表現するときに使う。ここにある機能を採用すること自体を目的にしない。

## Dataとdomain

- `@dataclass(frozen=True)`: immutableな値や明示的なinput/resultに使う。validationが必要なら`__post_init__`またはfactoryを検討する。
- `Enum`: 許可された有限状態を表す。状態遷移ruleはEnumへ詰め込む必要はない。
- `NewType`: static type checkerによるID等の取り違え防止に使う。runtimeでは元の型である点を明記する。
- plain function: 状態を持たないoperationやdependencyを明示的に引数で渡せる処理では、classより先に検討する。

## Structural typing

consumerが必要とする小さな契約には`typing.Protocol`を使える。

```python
class Clock(Protocol):
    def now(self) -> datetime: ...
```

runtime checkが必要でなければ`@runtime_checkable`を付けない。Protocolにprovider固有methodを増やさない。

## Package facade

```python
# ordering/__init__.py
from .model import Order, OrderId
from .place_order import PlaceOrder, PlaceOrderResult

__all__ = ["Order", "OrderId", "PlaceOrder", "PlaceOrderResult"]
```

facadeは安定させたい公開面がある場合に使う。application内部の小packageへ一律に作らない。

## Dependency injection

- constructorまたはfunction argumentを既定にする。
- object graphはentrypoint近くのcomposition rootで組み立てる。
- service locatorやglobal mutable singletonを安易に導入しない。
- frameworkのDI containerを使う場合も、domain/use caseをcontainer APIへ依存させない。

## Import

- projectの既存規約を優先する。
- package間は読み手がownerを追いやすいabsolute importを基本候補にする。
- package内部の明確なprivate relationではrelative importも許容する。
- import cycleは共通moduleへ移す前に、相互依存する意味やstate authorityを再評価する。
- 型注釈のためだけのcycleなら`TYPE_CHECKING`やforward referenceを使えるが、runtime依存のcycleを隠さない。

## Sync/asyncと例外

- sync/async境界はentrypointまたはadapterへ寄せ、domain modelへevent loop事情を漏らさない。
- vendor例外はadapterで意味あるapplication failureへ変換する。
- 捕捉して回復できない例外を抽象化のためだけにwrapしない。
