# ナレッジ管理DB(OpenShift デモ)

Python 標準ライブラリ + SQLite だけで動く、ナレッジの登録・検索 Web アプリです。

- `/` キーワード検索(タイトル・カテゴリ・タグ・本文の部分一致)
- `/new` 新規登録
- `/healthz` ヘルスチェック

## ローカル実行
```powershell
$env:DB_PATH="./data/knowledge.db"; python app.py   # http://localhost:8080
```

## OpenShift へのデプロイ(Web コンソール / GUI)

前提: このフォルダ(`Dockerfile` と `app.py`)を Git リポジトリ(GitHub 等)に push 済みであること。

1. 右上のプロジェクト選択から **プロジェクトの作成** で `knowledge-demo` を作成する。
2. **Developer** パースペクティブで **+Add** → **Import from Git** を開く。
3. 入力内容:
   - Git Repo URL: 自分のリポジトリ URL
   - Context dir: `/knowledge-db`(リポジトリ直下に置いた場合は空欄)
   - Import Strategy: **Dockerfile**(自動検出されます。Dockerfile のパスは `Dockerfile`)
   - Application name / Name: `knowledge-db`
   - Resources: **Deployment**
   - Advanced options → **Target port**: `8080`、**Create a route** にチェック(Secure Route を使う場合は TLS を Edge、Insecure traffic を Redirect に設定)
4. **Create** を押す。BuildConfig が作成されてビルドが始まる。**Topology** 画面でビルド状況を確認できる。
5. データを永続化する場合(任意):
   - **Storage** → **Create PersistentVolumeClaim** で `knowledge-db-data`(1GiB、ReadWriteOnce)を作る。
   - Topology でアプリを選択 → **Actions** → **Edit Deployment**(または Administrator の Workloads → Deployments → `knowledge-db` → Storage)で **Add Storage** を選び、既存の PVC を **Mount path** `/data` にマウントする。
   - PVC を付けない場合、データは Pod 再起動で消える(デモだけなら問題ない)。
6. Topology のアプリアイコン右上にある **Open URL** から画面を開く。

### YAML をまとめて GUI から投入する場合
先にイメージをビルド済みにしてから、右上の **+**(Import YAML)に `openshift/deploy.yaml` の内容を貼り付けて **Create** を押す。`image:` の値は内部レジストリ上の実際のイメージ名に合わせる。

## OpenShift へのデプロイ(CLI、参考)

### 方法A: BuildConfig(Docker戦略)でクラスタ内ビルド
```bash
oc new-project knowledge-demo
oc new-build --name knowledge-db --binary --strategy=docker
oc start-build knowledge-db --from-dir=. --follow
oc apply -f openshift/deploy.yaml
oc get route knowledge-db
```

### 方法B: ローカルで build して push
```bash
podman build -t <registry>/knowledge-demo/knowledge-db:latest .
podman push <registry>/knowledge-demo/knowledge-db:latest
oc apply -f openshift/deploy.yaml   # image: を合わせて編集
```

## ビルドが速い理由
pip install を行わず、Dockerfile は `COPY app.py` のみ。ベースイメージがキャッシュ済みなら数秒で完了します。

## 注意
- SQLite を使うため `replicas: 1` 固定です(デモ用途)。
- データは PVC(`/data`)に保存され、Pod 再起動後も残ります。
