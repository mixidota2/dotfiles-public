---
name: design-python-code
description: Pythonコードのpackage・module・class・functionの配置と責務、依存方向、公開API、domain model、外部依存境界を設計・実装・レビューする。Pythonプロジェクトのディレクトリ構成を決める、package直下に増えた.pyを再編する、巨大なservices.py/models.py/utils.pyを分割する、新機能の配置を決める、SRP・OCP・凝集度・結合度・変更局所性を改善する、Protocol・port/adapter・Strategy等の抽象化要否を判断する依頼で使う。単純な構文・bug修正、format/lint、依存library利用、設計済み依存ruleの機械的設定、patternの概念説明だけ、複数system・teamの合意用Design Doc作成では使わない。
---

# Pythonコードを設計する

Pythonコードの境界を、見た目やpattern名ではなく、実際の責務・状態・依存・変更シナリオから決める。既存構造を調べ、必要な最小変更を候補として作り、責務・owner・依存と変更局所性を反証してから提案または実装する。

## 作業モードを決める

依頼を次のモードへ分類する。必要なら複数を組み合わせる。

- `architecture`: project内のpackage境界と依存方向を設計する。
- `module`: package内のfile、class、functionを分割・統合・移動する。
- `domain`: 状態、不変条件、業務操作、状態変更権限を設計する。
- `boundary`: 公開API、Protocol、外部system・frameworkとの境界を設計する。
- `implementation`: 合意済みまたは依頼された設計をコードへ反映する。
- `review`: 既存コードや差分の設計上の問題を証拠付きで指摘する。

設計依頼では提案までに留め、実装依頼がある場合だけ編集する。レビュー依頼ではread-onlyを保つ。

## 必須ワークフロー

1. 対象repositoryの`AGENTS.md`、tree、entrypoint、設定・依存注入、公開API、test配置を確認する。既存方式を推測で置き換えない。
2. actor、達成したいこと、成功条件、変更範囲、既知の制約を整理する。指定されたpattern名は目的ではなく候補手段として扱う。
3. 異なる軸から代表的な変更シナリオを2〜5個挙げる。各シナリオについて、変更すべき場所と変更が波及してはいけない場所を定める。技術分類を横断して同時変更されるfile群がある場合、その変更理由を一つのcapability・処理段階・variantへ閉じ込められないか検討する。
4. 業務上の意味、状態、不変条件、semantic owner、state authority、source of truth、外部依存を特定する。確認済み事実、仮定、未確認事項を分ける。
5. 現状維持を含む最小案を最初に評価する。directoryや抽象化は、実在する責務境界・variation・交換またはtest上の必要性がある場合だけ追加する。
6. 作業モードに対応するreferenceを読み、提案または実装へ反映する。
7. 設計結果には、提案tree、各package/moduleの責務と非責務、公開面、依存方向、主要なtrade-offを含める。複数のentrypoint・pipeline・実験経路がある場合は、共有するuse caseと各経路に残す責務も示す。既存構造が妥当なら、再編しない理由を示す。
8. 推奨案を確定する前に`references/design-validation.md`の独立したself-reviewを行う。候補→反証→修正→同じrubricで再評価し、新規境界ごとのMerge/Deleteとentrypointごとの推移的依存を記録する。根拠付きの`Pass / Revise / N/A`を示し、未解決の`Revise`や未確認の判断を合格として扱わない。
9. 実装した場合は`references/implementation-validation.md`で差分、test、lint/type check、必要なimport boundary checkを検証する。設計・reviewのみなら検証計画と未実行を区別し、編集しない。
10. 結論から報告し、変更内容、検証結果、残る仮定・risk・未完了事項を区別する。

## Referenceの選択

`references/core-principles.md`は常に読む。その上で、該当するものだけ読む。

- project・package境界、feature/capability分割、composition root: `references/architecture-and-packages.md`
- flat package、巨大module、file/class/functionの分割・統合: `references/module-decomposition.md`
- entity、value object、状態遷移、不変条件、writer: `references/domain-modeling.md`
- 公開API、Protocol、port/adapter、外部例外、retry: `references/interface-boundaries.md`
- Pythonでの具体的な表現方法: `references/python-techniques.md`
- 候補設計・reviewでの反証と再評価: [design-validation.md](references/design-validation.md)
- 実装後のtest・品質check、またはその検証計画: [implementation-validation.md](references/implementation-validation.md)
- 既存リンクから検証先を選ぶ互換entrypoint: [validation.md](references/validation.md)
- 既存コードまたはdiffのreview: `references/implementation-review.md`

## 完了条件

- 提案が確認したコード・設定・用語に基づいている。
- 主要な責務、所有する状態、公開面、依存方向を追跡できる。
- 代表変更が無関係なmoduleへ不必要に波及せず、異なる軸の反証にも耐える。
- 新規境界のMerge/Delete、各entrypointの推移的依存、10観点の根拠付き判定を追跡できる。
- 推奨案には`Revise`が残っていない。証拠不足なら必要な確認と暫定案を示し、検証済みと称さない。
- 新しい抽象化ごとに、現在の必要性または実在するvariationを説明できる。
- 設計のみ、review、implementationの変更権限を守っている。
- 実装した場合は、関連testと品質checkの結果を報告している。
