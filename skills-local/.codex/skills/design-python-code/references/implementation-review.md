# 実装とdiffのreview

reviewでは先にfindingを重要度順で示す。要約より、正しさ・変更容易性・不正状態・依存漏出に関する具体的な問題を優先する。

## 調査順

1. diffだけでなく、変更されたsymbolのcaller、test、設定、entrypointを読む。
2. 変更が実現しようとする利用者目的と代表変更シナリオを特定する。
3. 新旧の責務、状態owner、公開契約、依存方向を比較する。
4. findingごとに実際のfile・line・symbolを証拠として示す。
5. findingがなければ、その旨と残るtest gap・未確認事項を示す。

## 確認項目

- 業務ruleがhandler、ORM、serializer、CLIへ漏れていないか。
- 同じ状態を複数のwriterが独立に変更できないか。
- internal file pathがpublic consumerへ露出していないか。
- framework、SDK、DB固有型・例外がdomain/use caseへ漏れていないか。
- 新providerやvariant追加のたびにcallerへ条件分岐が増えないか。
- 一実装しかない抽象化が理解と変更を難しくしていないか。
- import cycleを遅延import等で隠していないか。
- testがimplementation detailではなく契約・不変条件・failureを検証しているか。
- userの対象外変更や不要なrename・formatが混ざっていないか。

## Findingの形式

```text
[severity] 問題の結論 — file:line
Evidence: 確認できるcode上の事実
Impact: 破られる不変条件または影響する変更シナリオ
Minimal fix: 最小の修正方針
Residual risk: 修正後も残るriskまたは未確認事項
```

設計の好みだけをbugとして報告しない。alternativeを提案する場合は、現行案が具体的にどのscenarioで失敗するかを示す。
