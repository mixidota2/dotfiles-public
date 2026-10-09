# 候補設計を反証する

変更が局所化していても、誤った概念やownerを前提にした候補は棄却する。設計を推奨する前に、以下を独立したself-reviewとして行う。小規模な構成も同じ観点で確認するが、新しいlayerやProtocolを作ることを合格条件にしない。

## 候補 → 反証 → 修正 → 再評価

1. 確認したuse case、entrypoint、状態・不変条件、外部作用、公開契約、設定・DIを候補のownerへ対応付ける。codeのfile/symbol、要件の項目、userが明示した制約を根拠として識別できるようにする。treeや名称だけから新しい業務概念を事実として作らない。
2. 現状維持またはより小さい候補と比較し、下記の反証と異なる軸の変更シナリオを流す。成功例だけでなく候補を壊す例を探す。
3. 10観点すべてに`Pass / Revise / N/A`と根拠を付ける。適用される観点を省略せず、`N/A`は対象が存在しない理由を示す。`Pass`には確認した事実と反証結果が必要で、名称や「問題なし」だけでは足りない。
4. `Revise`があればowner、境界、公開契約、依存または前提を最小限修正する。旧候補の失敗と修正箇所を残し、変更後の候補を同じ10観点で再評価する。影響のない観点は同じ根拠を再利用してよいが、変更で無効になっていないか確認する。
5. 適用対象に`Revise`が残らない候補だけを推奨する。証拠不足で判定できない観点は`Revise（未確認）`とし、確認事項・確認先と暫定案を出す。仮定が条件付きで合理的でも、確認済みの`Pass`や`N/A`へ置き換えない。新しい証拠を得られないままloopを繰り返さず、必要な確認を明示して止める。

read-only reviewではコードを変更せず、候補上の修正と再評価を行う。現行コードに問題が残る場合はfindingとして報告し、修正済みと称さない。元から妥当な候補には、loopを示すためだけの欠陥や変更を作らない。

## 10観点のrubric

各判定を`観点 | 判定 | 根拠・反証結果 | 必要な修正/確認`で短く示す。同じ証拠を参照してよいが、観点ごとの結論は分ける。

| 観点 | 棄却すべき状態・確認する証拠 |
| --- | --- |
| Coverage | use case、entrypoint、所有状態、不変条件、外部作用にowner不在や隠れた実行経路がある。入力から結果までの対応表とtraceで確かめる。 |
| Ownership | 同じ判断・不変条件・状態を独立した複数ownerが支配する。semantic owner、state authority、source of truthを区別し、alternate writerも調べる。 |
| Cohesion | 同一module内に異なる意味・変更理由が混在する、または一つの変更理由が技術分類へ散る。実際のsymbolと同時変更範囲で確かめる。 |
| Dependency | 逆向き依存、cycle、具体型・例外・初期化の漏出がある。直接importだけでなくentrypointからの推移的依存と実行時の呼出し・注入を追う。 |
| Abstraction necessity | package、module、Protocol等の境界に現在の責務・variation・隔離・test上の根拠がない。新規境界ごとのMerge/Delete結果を示す。 |
| Orchestration | 処理順序、集約、failure、transaction、retry/重複排除の責任が重複・欠落する。該当する実行経路で誰が決めるか確認する。存在しないtransactionを捏造しない。 |
| Changeability | 異なる軸の変更が無関係なmoduleへ波及する。変更先・非波及先と守る契約を具体化する。 |
| Cognitive load | treeと名称から入口、主要処理、結果・外部作用へ辿れない、または薄い転送層が理解を増やす。name-blind説明と実行traceで確認する。 |
| Evidence | 判定を支える事実が設計対象の範囲で十分かを確認する。確認済み・仮定・提案・未確認と出典を分けるだけでは合格にならない。候補の妥当性を左右する概念・要件・caller・runtime制約等が未確認なら、誠実に開示していても`Revise（未確認）`。明示された仮想システムの事実はその設計範囲の証拠として使い、範囲外の不明点まで理由にしない。 |
| Simplicity | 同じ制約を保つ現状維持・統合・削除案がより小さく理解しやすい。file数だけで決めず、責務と必要な隔離を失うか比較する。 |

## 境界のcounterfactual check

新しく作るpackage・module・interfaceの各境界を列挙し、少なくともMergeとDeleteの両方を記録する。同じ根拠のものはまとめてもよいが、対象名を漏らさない。既存境界も、変更対象または失敗に関係するものを確認する。

- **Merge:** 隣接するownerへ統合したら、どの責務・不変条件・変更の隔離が失われるか。失うものがなく理解が容易になるなら統合する。別fileに見えることは根拠にならない。
- **Delete:** 境界を取り去ったら、owner不在になる責務・必要な契約は何か。薄い転送だけなら直接呼出しと比較する。compatibility facadeなど既存consumerが必要とする境界はその契約を根拠に残す。
- **Dependency inversion:** 主要な依存を逆転したら、どちらが相手の都合を知るか。依存を逆転するためだけのProtocolは増やさず、単純な引数・callable・既存DIとも比較する。
- **Replacement:** 実在するprovider・UI・algorithm等の交換時に、変更がどこまで届くか。交換予定がない場合はそう示し、架空のvariationを作らない。
- **Entry-point trace:** 各entrypointから結果・side effectまで、責務、データ/状態、failure ownerを辿る。共有区間は参照してよいが、入口固有の経路を省略しない。
- **Name-blind:** module名やpattern名を使わず、誰の何を決め、何を決めないか説明する。説明が同じ境界は統合候補、説明できない境界は根拠不足として扱う。

entrypoint traceには、公開facade、re-export、設定・DI、実際に選択される実装を含める。`入口 → 共通処理 → 注入実装 → 外部作用/結果`のcall pathに加え、import・型・例外・初期化が運ぶ推移的依存を示す。runtimeの呼出し方向とsourceの依存方向を混同しない。直接importがなくても下流の具体型やSDK初期化がcoreへ到達するなら隔離できていない。参照不能な辺は未確認として残す。

## 異なる軸の変更シナリオ

対象に合う2〜5個を異なる軸から選ぶ。同種providerの追加ばかりで候補を追認しない。対象外の軸を無理に追加する必要はない。各scenarioで次を記録する。

```text
- 変更内容と選んだ軸
- 変更すべきmodule / 変更してはいけないmodule
- 守る公開契約・不変条件
- 反証結果、必要な修正・確認、実装時のtest
```

軸と候補:

- 業務rule・状態遷移: 既存条件や判断を変更する。
- consumer・entrypoint: 同じuse caseを別のCLI、Notebook、pipeline、APIから実行する。
- 外部provider・variant: DB、HTTP client、SDK、保存先、algorithmを交換・追加する。
- capability削除: featureを取り去り、孤立する依存や不要な共通層を調べる。
- failure: timeout、部分成功、同じ要求のretryと重複を扱う。
- 状態・データ形式: state authority、保存形式、consumerへの表現を変える。
- runtime・dependency制約: orchestratorや実験環境の交換、依存libraryの利用制約を変える。
- 内部配置: public contractを保ってmoduleをrename・splitする。

無関係なmoduleへ変更が波及する場合、責務境界、公開契約、状態ownerのどれが曖昧かを調べる。

algorithmやproviderを持つ構造では、「既存variantの変更」と「新規variantの追加」を分けて流す。前者がvariant package外へ散るなら凝集が弱く、後者が複数callerの分岐変更を要求するならvariation pointが散っている可能性がある。学習・推論・固有前処理は既存variant変更に含める。

複数の実行形態を持つ構造では、同じ振る舞いの変更をCLI、Notebook、pipelineへ重複実装せず、共有use caseとそのtestだけで反映できるか確認する。orchestrator交換時にdomain・algorithm・use caseの変更が必要なら、外部依存境界を再評価する。

## 報告する結果

提案tree、責務・非責務、公開API、設定・DI、依存方向、trade-offをself-review表で置き換えない。その設計に、最初の候補から変わった箇所と理由、境界check、entrypoint trace、最新rubric判定を添える。根拠は共有して簡潔にし、全過程の長い作業日誌にしない。

未確認が残る場合も、確認済み範囲の結論、暫定案、判定を変える最小の追加情報を示す。全情報が揃うまで有用な分析を止める必要はないが、未検証の推奨や実装完了を主張しない。
