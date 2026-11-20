# 外部パッケージ不要(標準ライブラリのみ)のため、ビルドは COPY のみで数秒で完了します。
FROM registry.access.redhat.com/ubi9/python-312

ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/data/knowledge.db \
    PORT=8080

WORKDIR /app
COPY app.py .

# OpenShift は任意UID(グループ0)で実行するため、グループに書き込み権限を付与
USER 0
RUN mkdir -p /data && chgrp -R 0 /data /app && chmod -R g=u /data /app
USER 1001

EXPOSE 8080
CMD ["python", "app.py"]
