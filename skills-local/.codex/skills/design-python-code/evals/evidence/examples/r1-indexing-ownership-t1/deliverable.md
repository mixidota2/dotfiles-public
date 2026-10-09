# ローカル文書検索サービスの設計レビュー

## 結論

**多段のmanager／repository構成は採用せず、現行のフラット構成を維持する。** `services.py` の `index_directory` をCLI・HTTP API共通のユースケースとし、ID正規化の実装をそこへ一本化する。`storage.py` は渡されたIDを変更せず保存する。純粋なparserとcallerによる注入を維持する。

`application/index_service.py`、`DocumentManager`、転送専用の`DocumentRepository`、`orchestration.py`、`domain/document.py`、一律のProtocol／Factoryは追加しない。今回確認できる要件には、それらの独立した状態・権限・交換理由がない。

構造についてはこの最小案を選べる。一方、**既存の戻り値・例外、repositoryのroot単位、保存の原子性が未提示なので、失敗時の動作とデータ移行は後述の確認を通してから確定する。** 未確認部分を含む設計全体を検証済みとはしない。コード変更・テスト実行は行っていない。

## 1. レビューの根拠と重要な指摘

根拠は依頼文にある「現行の確認済み処理」「既存公開API」「同僚の案」「今後確実な変更」。対象ディレクトリには依頼文と設計資料だけがあり、実装、`AGENTS.md`、設定ファイル、テストコードはない。以下のsymbol参照は依頼文の記述に基づき、実コードの行番号は示せない。

### [高] IDの意味を複数箇所で決めると、安定性を保てない

- 根拠：現行の`services.py`と`storage.py:SqliteRepository`が別実装で正規化する。同僚案ではさらに`DocumentRepository`と`domain/document.py`へ判断が分散する。
- 影響：ID規則変更時に実装がずれると、CLI/APIが認識するIDと保存キーが一致しない。旧キーが残る、新キーが衝突するなどの可能性がある。現在テストが通っていることだけでは、将来の規則変更の安全性を示せない。
- 最小修正：IDの算出・正規化を一つの純粋関数にまとめ、共有ユースケースから一度呼ぶ。保存層の独自正規化を除く。保存層は必要な妥当性検査をしても、IDを書き換えない。
- 残る確認：既存データがどちらの実装の結果で保存されているか。直接`upsert`する別のcallerがないか。

### [高・条件付き] 相対pathだけでは、複数rootを一つの保存先に入れたとき一意にならない

- 根拠：`root_A/a.md`と`root_B/a.md`は、どちらも相対IDが`a.md`になる。repositoryがrootごとに分かれるかは記載がない。
- 影響：同じrepositoryを共有すると別文書の上書きが起こり得る。これは「再実行時の重複防止」とは別の問題。
- 最小の暫定前提：**一つの索引のID名前空間は一つのrootに対応する。** 既存callerがこの条件を満たすか確認する。現行の設定読込・DIを置き換えない。
- 複数root混在が必須なら：索引の名前空間をどう識別するかを先に決める。rootを勝手にIDへ加える、公開引数を勝手に増やす、といった変更はしない。既存APIのまま実現できる保存境界を追加検討する。

### [中] 転送層と文書の二重所有が、変更箇所と理解の負担を増やす

- 根拠：`application/index_service.py`は引数を渡すだけ。`DocumentManager`、`DocumentRepository`、`domain/document.py`が同じID・本文・状態を所有する案になっている。
- 影響：更新を決定する場所と、正として保存する場所が曖昧になる。ID修正のたびに複数層を追う必要があり、独立した責務は増えていない。
- 最小修正：処理順序と保存する内容の決定は`services.py`、永続化とDB制約は`storage.py`。解析結果は一処理のローカルな値として受け渡す。managerが保持する別の文書状態は作らない。

### [中] 一律のProtocol／Factoryは、現在のvariationを説明できない

- 根拠：SQLite以外の保存先追加は当面なく、parserは純粋関数、repositoryとparserはすでにcaller注入である。
- 最小修正：既存の注入方式と型定義を維持する。parserは関数として扱い、必要な型注釈には既存の解析結果型と`Callable`で足りる。repositoryは既存の`upsert(id, text, metadata)`契約を明文化する。
- 再検討条件：型検査で注入先の契約が表現できない、失敗注入用fakeとの共有契約が必要、具体DB型の漏出が確認された、など。そうなった場合だけconsumer側の小さなRepository Protocolを検討する。Protocol導入はFactory導入の理由にはならない。

## 2. 採用する最小構成

依頼文から分かる現行構成は、`cli.py`と`api.py`が`services.py`を呼び、`parser.py`と`storage.py`を利用する形である。公開importの実装位置は未確認。

提案するtree：

```text
indexkit/
├── __init__.py    # index_directoryの既存公開面を維持
├── cli.py         # CLI入力と表示・終了コード
├── api.py         # HTTP入力とレスポンス・ステータス
├── services.py    # 共通index_directory、ID規則、共通の結果・失敗の意味
├── parser.py      # strから解析結果への純粋な変換
└── storage.py     # SqliteRepository、SQLiteへの保存

既存の設定読込・DI・テスト配置：維持
```

`__init__.py`がすでにre-exportを持つならそのまま使う。公開面のための薄いre-exportは、無目的な転送サービスとは異なり、`indexkit.index_directory`の互換性を守る役割がある。

| 場所 | 責務・所有するもの | 担当しないもの |
|---|---|---|
| 公開面 | `indexkit.index_directory(root, repository, parser)`への安定した入口 | 設定読込、具象実装の生成、新しい業務処理 |
| `services.py` | path列挙、rootからの相対ID算出、本文読込、解析の呼出し、保存する値の決定、結果集約・失敗方針 | Markdownの文法、SQL、HTTP形式、CLI整形、永続的な文書キャッシュ |
| `parser.py` | 本文の解析規則と解析結果。入力は`str` | path列挙、ID正規化、DBアクセス、CLI/API応答 |
| `storage.py` | 渡されたID・本文・metadataの永続化、キー一意制約、保存単位の原子性、SQLiteエラーの境界変換 | IDの意味の再定義、再正規化、文書解析、ディレクトリ全体の進行方針 |
| `cli.py` | 入力変換、既存の注入経路の利用、共有結果のCLI表現 | ID規則、解析、保存、独自の再試行・成功判定 |
| `api.py` | HTTP入力変換、既存の注入経路の利用、共有結果のHTTP表現 | ID規則、解析、保存、独自の再試行・成功判定 |

### IDを新しいdomain packageへ移さない理由

ID規則には一つのownerが必要だが、独立したpackageやentityは必要ではない。現時点での唯一の共通処理に、例えば`_document_id(root, path)`という純粋な内部関数として置けばよい。ユースケース全体とは独立に単体テストできる。

もしID生成が複数の別ユースケースから実際に使われるようになったら、同じ関数を`document_id.py`へ移すことは検討できる。その時も保存層に第二の実装を作らない。今回、先回りしてmoduleを増やす必要はない。

### 状態と権限

- IDのsemantic owner／ID規則の不変条件：`services.py`の単一関数。
- 文書を解析し、どの値で索引を更新するかの決定権：`index_directory`。
- 入力本文のsource of truth：読み込むローカル文書。ただし、metadataまで全て再構築可能かは未確認。
- 永続化済み索引のsource of truth：SQLiteの保存データ。
- 保存writer：注入されたrepositoryの`upsert`。重複しない永続キーの実装責任はSQLite側にもある。
- 解析途中の本文や結果：呼出し中だけの値。managerとrepositoryがそれぞれ持つ独立した可変状態にしない。

IDの意味を決める責任と、DBが同じキーを二行保持させない責任は異なる。DBの一意制約は残すが、第二の正規化は持たせない。

## 3. 公開契約・ID・失敗の扱い

### 維持する契約

- 公開呼出しは`indexkit.index_directory(root, repository, parser)`のまま。引数の順序・キーワード名、同期／非同期の形を変更しない。
- callerが渡したrepositoryとparserをそのまま利用する。内部でSQLiteやparserの既定実装を生成しない。
- `repository.upsert(id, text, metadata)`とparserの既存入出力を維持する。戻り値型、例外型、metadataの意味まで確認して互換性を守る。
- 内部moduleの整理を理由に、既存callerへ新しいimport、Factory、設定を要求しない。

### ID規則で固定すべきこと

まず二つの現行正規化の実例を採取し、既存の期待IDを固定する。パス区切り、`.`／`..`、大小文字、Unicode、symlinkの扱いを推測で変更しない。

新しい規則を決める際は、以下を一つの仕様・テスト群にする。

1. 許可されたroot内の相対pathから、決定的にIDを作る。
2. 同じroot・同じ文書・同じ規則なら同じIDになる。絶対root名をIDへ混ぜない。
3. 異なる入力pathが同じIDになる場合は、黙って後勝ち保存しない。変更予定の規則で衝突が起こらないか検出する。
4. root外、symlink、case-sensitiveなfilesystemとcasefoldingの組合せなどを明示する。`resolve()`や小文字化を無条件に入れない。
5. ID規則の変更はデータ移行を伴い得る。新規則で単に`upsert`し直すだけでは旧IDの行が残る。

同じ文書を再実行して索引行数が増えないことと、複数の別文書が衝突しないことは、別々に検証する。

### CLI/APIで共有する失敗契約

共通化するのは失敗の意味と保存結果であり、HTTPステータスとCLI終了コードを同じ値にすることではない。共有ユースケースから返った同じ事実を、それぞれの入口が表現する。

現行の戻り値・例外仕様がないため、新しい公開`IndexResult`型を既成事実として追加しない。次の情報を**既存の戻り値／例外表現へ対応付ける**。既存契約では表現できない場合だけ、互換性のある拡張を別途決める。

- 対象path、算出済みならdocument_id。ID算出前の失敗に架空のIDを付けない。
- 失敗段階と安定した分類。例：入力／列挙、ID衝突、本文読込、解析、保存。
- 成功済み件数、失敗した文書、未処理の有無。途中停止を全件失敗や全件成功へ丸めない。
- 保存が確実に失敗したのか、確定を確認できないのか。件数と原因を生の例外文字列だけに依存させない。

失敗の分類・集約方針は`services.py`のownerとする。SQLiteの型・エラーコードの解釈は`storage.py`で止め、共有契約へ変換する。必要な共通例外が既にあるなら再利用し、なければ最小の定義を共通ユースケース側に置く。CLIとAPIはSQLエラーを個別に解釈しない。parserは純粋性を保ち、宣言された解析失敗をユースケースで共通の結果へ対応付ける。

**現行動作を確認してから採否を決める暫定の実行方針：**

| 発生箇所 | 方針案 | 保存状態の扱い |
|---|---|---|
| 無効root／初期列挙失敗 | 開始できない理由を返す | 書込み前なら変更なし。途中の列挙失敗なら成功済み分を明示 |
| ID衝突 | 書込み前のpath・ID検査で拒否 | 当該実行からの書込みなし。小規模なので事前検査を候補とする |
| 読込／宣言された解析失敗 | 文書単位で記録して継続 | その文書をupsertしない。以前の索引があれば旧内容が残る旨を示す |
| 保存失敗 | 以降の保存を停止し、成功済み・失敗・未処理を区別 | 既存のcommit単位に従う。失敗した保存を確認なしに成功件数へ入れない |
| 予期しない実装例外 | 既存のエラー境界へ伝える | 一律catchで通常の文書エラーや成功へ変換しない |

ディレクトリ全体のrollbackや自動retryを新設しない。保存一件の原子性・成功確定条件はrepository契約として確認する。再実行は同じIDへのupsertで重複を防ぐが、これはディレクトリ全体の原子性を意味しない。現行がfail-fastなら、この整理だけで継続方式へ切り替えない。

## 4. 入口から保存までと依存方向

### 呼出し・データの流れ（提案）

- CLI：引数変換 → 既存の設定・DIで受け取るroot／repository／parser → `services.index_directory` → 共通区間 → CLIの結果表示・終了コード。
- HTTP API：リクエスト変換 → 既存の設定・DIで受け取る同じ依存 → `services.index_directory` → 共通区間 → HTTPレスポンス・ステータス。
- 外部Python caller：`indexkit.index_directory` → 既存re-export経由で同じ`services.index_directory` → callerが渡した依存 → 既存契約の結果／例外。
- 共通区間：path列挙 → ID関数 → 本文読込 → 注入parser → 注入repository.upsert → 共通結果の集約。実際に注入されるrepositoryが`SqliteRepository`ならSQLiteへ保存する。

CLI/APIを公開facade経由へ書き換えること自体は目的にしない。現在の`services.py`呼出しを維持しても、同じ関数が公開面から利用できれば要件を満たす。

### source／型／例外／初期化の依存

```text
indexkit.__init__ ──re-export──> services
cli / api ──import──> services
services ──import──> 必要な標準ライブラリ・既存の中立的な型
services ──runtime call──> caller注入parser / repository
storage ──import──> sqlite3・必要ならconsumer側の共通失敗定義
既存の組立て箇所 ──> 具象repository / parser / 設定
```

`services.py`からHTTP framework、`sqlite3`、具象`SqliteRepository`、SQLite接続初期化へ依存させない。parserの型注釈経由でDBやHTTP依存が到達する構成にもさせない。`storage.py`が共通失敗定義を参照するなら、逆向きの`services → storage` importを作らない。公開facadeの読み込みだけでCLI/HTTP frameworkやDB接続を初期化しない。

これは**望ましい推移的依存の指定**であり、実コードのimport graphを検査した結果ではない。設定・DIの実ファイル、re-export、型注釈と例外、直接storage caller、fixtureや移行scriptを実装前に確認する。

## 5. 変更シナリオでの反証

| 軸・変更 | 変更する場所 | 波及させない場所・守る契約 | 反証／テスト |
|---|---|---|---|
| ID規則修正 | `services.py`のID関数とIDテスト。既存データは独立した移行手順 | parser、CLI/APIのID実装、storageの正規化。公開関数の引数を維持 | 二重正規化なら両方の修正が必要になるため棄却。新旧ID対応・衝突・再実行を検証 |
| Markdown解析修正 | `parser.py`とparserテスト | path・ID規則、SQL、CLI/API。解析結果の契約を維持 | 新しい解釈で同じ文書IDの本文が更新され、行数が増えないことを確認 |
| CLI出力形式修正 | `cli.py`と表示テスト | API、parser、storage、共有失敗の意味 | CLI整形を共有ユースケースへ置く案は棄却。API応答と保存値が変わらないことを確認 |
| 読込／解析／保存の途中失敗と再実行 | 共通の失敗方針は`services.py`、DB固有変換は`storage.py` | CLI/API個別の独自retryや例外分類 | 注入fakeで同じ失敗を再現し、共有結果・保存状態・再実行後の行数を照合 |
| 内部配置変更 | 必要になった場合だけ移動先とre-export | 外部callerのimport・引数・設定・DI | `from indexkit import index_directory`とcaller注入のconsumer test。今回のrename自体は不要 |

SQLiteの架空の後継providerは反証シナリオにしない。parser変更で出力契約自体が変わる場合は共有契約への影響があり、上表の「parserだけで完結」は契約を保つ変更に限る。

## 6. 境界を統合・削除したらどうなるか

新規境界は原則ゼロ。追加案と、今回変更に関係する既存境界を両方検討した。

| 対象 | Merge：隣接責務へ統合した場合 | Delete：取り去った場合 | 採否 |
|---|---|---|---|
| `orchestration.py` | 順序制御は既存ユースケースで足りる | 入口が直接ユースケースを呼べる | 不採用 |
| `application/index_service.py`と専用package | 転送を`services.py`へ戻しても意味は失われない | 公開入口から共有処理へ直結できる | 不採用 |
| `managers/document_manager.py`と専用package | 更新決定をユースケースへ統合できる | 文書の第二の可変状態が消える | 不採用 |
| `repositories/document_repository.py`と専用package | 保存は既存repository、ID規則はユースケースへ戻せる | 不要な転送・再正規化が消える | 不採用 |
| `domain/document.py`と専用package | ID関数を既存共有処理へ置けば不変条件を保てる | ID関数まで消すとowner不在だが、entity／packageは不要 | 不採用 |
| manager／repository／parserの一律Protocol・Factory | 現行の注入・関数・既存型へ統合できる | 今あるcaller注入を失わず型と生成層だけ除ける | 不採用。必要が証明された小さな契約だけ再検討 |
| 新規`document_id.py` | 純粋関数として`services.py`内へ置いても単一ownerと単体テストを維持できる | 独立moduleをなくしても規則自体は残る | 今回は追加しない |
| 既存`services.py` | CLI/APIへ分散すると同じ処理と失敗方針が複製される | 共通の利用者目的・集約のownerを失う | 維持 |
| 既存`parser.py` | I/Oの順序とMarkdown規則が混在する | 解析自体は必須。純粋関数の独立テストを失う | 維持 |
| 既存`storage.py` | SQL・DB例外がユースケースへ流入する | 永続化のwriterを失う | 維持。ID書換えだけ削除 |
| 既存`cli.py`／`api.py` | 出力変更の異なる理由とframeworkが混ざる | 必須の実行入口を失う | 維持 |
| 既存の公開facade | 内部moduleをcallerへ露出すると配置変更が波及する | `indexkit.index_directory`互換性を失う | 維持 |

名称を伏せても、責務は「同じ索引更新を実行する」「文字列を解析する」「決定済みのキーで保存する」「各入口で入出力を変換する」と区別できる。一方「受けて次へ渡す」だけの候補層は統合できる。

依存を逆転して共有処理がSQL型・SQL例外の詳細を知ると、保存方式の都合が失敗契約へ漏れる。既存の引数注入と境界での変換で防げるかを先に確認し、依存逆転のためだけにProtocolを作らない。

## 7. 候補の設計判定

A＝現状を変更しない案、B＝同僚案、C＝上記の最小修正案。`Pass`は記載された設計についての根拠付き判定であり、実装のテスト合格ではない。未確認は`Revise`のまま残す。

| 観点 | A／Bの判定・反証 | Cの判定・根拠 | 残る確認／修正 |
|---|---|---|---|
| Coverage | A：Revise。既存失敗動作が未提示。B：Revise。多段化しても結果・失敗のownerを補えていない | Revise（未確認）。三入口と共有区間は対応付けたが、隠れたwriterと現行失敗契約は調べられない | 実コードのcaller、fixture、移行script、戻り値・例外を確認 |
| Ownership | A：Revise。二つのID実装。B：Revise。IDと文書状態のownerがさらに重複 | Revise（未確認）。単一ID ownerと保存writerは分離したが、root名前空間と旧保存キーが未確認 | repositoryとrootの対応、直接upsert経路、新旧ID対応を確認 |
| Cohesion | A：Revise。IDの同じ変更理由が保存層へ散る。B：Revise。同じ文書判断が複数の技術層へ散る | Pass。ID変更は共通処理、Markdown変更は純粋parser、CLI表示はCLIへ局所化 | 出力契約の変更は別途影響分析 |
| Dependency | A／B：Revise（未確認）。呼出しの概要だけでは型・例外・初期化の推移的依存を証明できない | Revise（未確認）。提案する禁止依存・runtime呼出しは明示したが現物未検査 | facade、型、共通例外、設定・DIのimport graphを確認 |
| Abstraction necessity | A：Pass。既存の共有処理・解析・保存・入口に役割がある。B：Revise。転送層と一律抽象化に根拠がない | Pass。Merge/Deleteにより新規層を除去。既存の必要境界だけ維持 | repository Protocolは現在の必要性を確認した場合だけ |
| Orchestration | A／B：Revise（未確認）。commit・途中失敗・retry契約が未提示。Bの転送層でも解決しない | Revise（未確認）。方針ownerは一つだが、提案する失敗動作が既存互換か未確認 | 現行動作、upsertの原子性、一意制約、成功確定条件を確認 |
| Changeability | A：Revise。ID修正が二箇所。B：Revise。同じ修正がさらに多層へ波及 | Pass。確実な三変更と失敗・公開面の変更を各責務へ割り当てた | ID変更時の保存データ移行は必要な波及として明示 |
| Cognitive load | A：Pass。共有処理→解析→保存が追える。B：Revise。同義の転送・所有を何段も追う | Pass。現行入口から結果までのtraceを保ち、不要な転送を増やさない | 実コードのtraceは後で照合 |
| Evidence | A／B：Revise。提示情報だけで互換性や完全性を確定できない | Pass。依頼文の事実と提案・暫定前提・未確認を区別し、実装済みとは述べない | 他観点の未確認をPassへ置き換えない |
| Simplicity | A：Revise。二重正規化は残せない。B：Revise。同じ制約をより小さく満たせる | Pass。現行構成でID ownerを一つにする。新しい階層・生成方式を追加しない | 規模や実際の複数consumerが変わった時だけ再評価 |

反証後の修正は、ID ownerを増やす案を単一関数へ戻すこと、文書の二重所有を除くこと、転送層・一律抽象化を除くこと。これを同じ10観点で再評価した。Cにも未確認の`Revise`が残るため、**構造の最小候補として提示し、契約と移行まで確定済みの設計としては承認しない。** 追加で必要なのは、実コード・テストと現在のDBスキーマ／代表データの確認であり、別の抽象化を増やすことではない。

## 8. 移行手順

### 第1段階：現在の契約を固定する

1. 公開import、引数、戻り値、例外、CLI/APIの失敗表現をcharacterization testにする。
2. 両方のID正規化を同じpath一覧に適用し、サービス側IDと保存済みIDの差を採取する。root対応、unique key、upsert・commit実装、直接writerを調べる。
3. 上記の未確認事項が解消するまで、データを書き換える移行と失敗方針の変更は開始しない。

### 第2段階：挙動を保って責務だけ一本化する

1. 現在の実効的な保存IDを再現する単一のID関数を`services.py`にまとめる。「今後のID仕様変更」と同じ変更に混ぜない。
2. `services.py`から正規化済みIDを渡し、`SqliteRepository`の再正規化をなくす。二つが食い違う場合は、既存の公開・保存契約のどちらを保つかを先に決め、互換性破壊を隠さない。
3. 直接repository callerがあれば影響を確認し、移行対象として扱う。未確認のcallerに正規化済みIDを突然要求しない。
4. 公開API、caller注入、設定読込をそのままにし、既存・追加テストを実行する。

### 第3段階：失敗契約を共有し、ID規則を変更する

1. 共通の失敗意味・結果とCLI/APIの表現変換をそろえる。まず既存動作を維持し、継続／停止や戻り値の変更が必要なら別の互換性判断にする。
2. 新ID規則で全対象pathの新旧対応を事前計算する。多対一の衝突、rootの混在、所在不明の旧行を検出し、衝突を任意の上書きで解決しない。
3. 索引を元文書から完全に再構築できることを確認できた場合は、**別のSQLite索引へ全件再構築して照合後に切り替える方法を優先**する。旧ID行が残らず、旧DBをrollback用に残せる。既存callerがrepositoryを生成する仕組みは変更しない。切替手段は既存の接続・運用方式で確認する。
4. 切替時は書込みを止めて接続を閉じるなど、利用中のDBを安全に切り替えられる状態を作る。単に開いているDBファイルをrenameしてよいとは仮定しない。
5. 再構築できないmetadata等がある、または別DBへ切り替えられない場合は、その場で全消去しない。検証済みの新旧対応と退避に基づくtransaction内のキー移行を別途設計する。衝突が残るなら移行を止める。
6. 同じ入力をもう一度実行し、件数が増えず内容が一致することを確認する。問題があれば旧索引と旧規則の組合せへ戻せるようにする。

通常の`index_directory`へ「古い行を全削除する」動作を紛れ込ませない。削除済み文書のpruneは、現行要件で確認できないため今回の変更対象にしない。

## 9. 検証計画

以下は実装時に行う計画であり、今回実行した結果ではない。

| リスク | 検証内容 |
|---|---|
| 公開API／DIの破壊 | `from indexkit import index_directory`で既存呼出し。位置・キーワード引数、戻り値・例外を確認。callerのfake repositoryとparserが実際に使われ、内部で生成し直されないことを確認 |
| IDの不安定性 | 既存期待値を回帰テスト化。相対path、区切り、`.`／`..`、Unicode、大小文字、symlinkを決めた仕様どおり検証。異なるpathの正規化衝突も検証 |
| 二重正規化の残存 | spy repositoryで受け取るIDを照合。SQLiteに保存したIDが渡したIDと完全一致することをintegration testで確認 |
| 重複／上書き | 一時SQLiteで同じ文書を2回索引化し、ID集合・行数が不変。本文変更時は同じ行が更新される。別文書の衝突やroot混在を黙って上書きしない |
| CLI/APIの差異 | 同じroot・入力・注入失敗で共有結果のID、分類、成功件数、失敗対象、未処理を照合。transport表現の差だけを許す |
| 部分失敗 | 読込・解析・保存の各段階で失敗を注入。保存呼出しの有無、成功済み行、旧内容の残存、停止／継続、再実行後の状態を確認 |
| DB原子性／同時更新 | 実スキーマの一意制約とupsertを検証。HTTP等で同時実行を許す場合は同じIDの競合を追加検証。結果を確認できない失敗を成功扱いしない |
| parser変更の波及 | 既存parser単体テストとMarkdown回帰ケース。サービスとの入出力契約を確認し、ID・CLI/API表現に影響しないことを検証 |
| データ移行 | 旧IDを持つfixtureで新旧対応、衝突検出、件数・本文・metadata、再実行、途中失敗、rollbackを検証 |
| 推移的依存 | 公開importのsmoke testとimport graphを確認。coreからHTTP／SQLite具象への逆依存、型・例外経由の漏出、接続初期化、副作用・循環がないことを確認 |

既存のテスト実行方式、lint・型検査・format checkに従う。ツールが未提示なので新しい品質ツールの導入や架空の実行コマンドは指定しない。

## 10. 得失と残る確認

得るものは、既存callerを保ったまま、ID修正・Markdown修正・CLI出力修正の変更先を分けられること、そして同じ失敗を両入口で共有できること。代わりに`services.py`は一つの索引更新の順序とID規則を同じmodule内に持つが、現状の規模では許容できる。将来の大規模な文書ライフサイクルや複数の独立ユースケースを、今の案へ仮定として持ち込まない。

実装着手前に確かめる最小事項は次の四つ。

1. 公開関数の既存の戻り値・例外と、CLI/APIの失敗動作。
2. 一つのrepositoryに複数rootを格納するか、ID規則の具体例と既存保存キー。
3. unique key、commit単位、直接writer、再構築できないmetadataの有無。
4. 実際の公開re-export、設定・DI、型と例外を含むimport graph。

今回の成果は設計レビューと移行・検証計画であり、コード修正、DB移行、テスト合格の報告ではない。
