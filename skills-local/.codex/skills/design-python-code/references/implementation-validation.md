# 実装後の検証

実装した差分が公開契約・不変条件・failureと依存境界を守るか確認する。設計案の妥当性は[design-validation.md](design-validation.md)で別に判定する。testの成功だけで責務境界の妥当性を証明したことにしない。

設計・read-only reviewのみなら、以下は実装時の検証計画として示す。未実行のcheckを成功と報告せず、review中に修正や状態を変える検証を行わない。

## Testの対応

- domain invariant: 不正な生成と状態遷移を拒否する。
- use case: consumerから見たinput、result、failure、side effectを検証する。
- port contract: 複数adapterが同じ契約を満たすことを検証する。
- adapter integration: DB、HTTP、SDKとの変換とfailureを検証する。
- acceptance: entrypointから主要な利用者目的を検証する。
- import boundary: 禁止依存やcycleを必要に応じて機械的に検証する。

test種別を一律に追加せず、変更riskに対応するものを選ぶ。

## 実装時のcheck

1. 変更した責務に近いunit/contract testを実行する。
2. repository既定のlint、format check、type checkを実行する。
3. 公開importを変えた場合、consumer testまたはimport smoke testを実行する。
4. dependency directionを変えた場合、import graphまたはboundary toolを確認する。
5. 全体testは変更範囲とcostに応じて実行し、未実行なら明記する。

## 実装の完了判定

- treeがきれいに見えることではなく、代表変更が局所化している。
- 状態を不正に変更できるalternate writerが放置されていない。
- public contractがinternal file配置へ依存していない。
- 抽象化に実在する根拠がある。
- testが新しい境界とfailure contractを検証している。

- 実装差分が検証済み候補の責務・依存・公開面を変えた場合、設計rubricへ戻って再評価している。
- checkは対象・実行結果・未実行理由を区別し、関連testだけの成功を全体test成功へ拡張していない。
