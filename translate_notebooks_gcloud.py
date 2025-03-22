#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Jupyter Notebook Markdownセル 自動翻訳スクリプト (Google Cloud Translation API版)

指定ディレクトリ内のJupyter Notebook（.ipynb）のMarkdownセルを
Google公式Translation APIで日本語に翻訳し、新しいファイルとして保存

【使い方】
--------------------------------------------------
1. Google Cloud プロジェクト & Translation API を有効化
2. APIキーを取得し、環境変数に設定
   export GOOGLE_API_KEY="<your api key>"

3. ライブラリをインストール
   pip install google-cloud-translate==3.11.2

4. 実行コマンド
   python translate_notebooks_gcloud.py /path/to/notebook-directory
--------------------------------------------------
"""

import os
import json
import logging
from typing import Optional
from google.cloud import translate_v2 as translate

# ログ設定
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 環境変数からAPIキーを取得
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    logger.error("環境変数 'GOOGLE_API_KEY' が設定されていません。")
    exit(1)

# クライアント作成
translate_client = translate.Client(api_key=GOOGLE_API_KEY)

def translate_text(text: str, target_lang: str = 'ja') -> str:
    """
    Google Cloud Translation APIを使ってテキストを翻訳する
    """
    if not text.strip():
        return text

    try:
        result = translate_client.translate(text, target_language=target_lang)
        return result['translatedText']
    except Exception as e:
        logger.error(f"翻訳に失敗しました: {e}")
        return text

def translate_markdown_cells(input_path: str, output_path: Optional[str] = None) -> None:
    """
    Notebookファイルを読み込み、Markdownセルを日本語に翻訳して保存する
    """
    logger.info(f"Notebook読み込み: {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
    except Exception as e:
        logger.error(f"ノートブック読み込み失敗: {e}")
        return

    translated_any = False
    for cell in notebook.get('cells', []):
        if cell.get('cell_type') == 'markdown':
            original_text = ''.join(cell.get('source', []))
            translated_text = translate_text(original_text)

            if translated_text != original_text:
                translated_any = True
                cell['source'] = [translated_text]

    if not output_path:
        dirname, filename = os.path.split(input_path)
        output_path = os.path.join(dirname, f"translated_{filename}")

    if translated_any:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, ensure_ascii=False, indent=2)
        logger.info(f"翻訳済みノートブック保存: {output_path}")
    else:
        logger.info(f"Markdownセルの翻訳対象なし: {input_path}")

def translate_notebooks_in_directory(directory: str) -> None:
    """
    指定ディレクトリ内の全ての.ipynbファイルを翻訳
    """
    if not os.path.isdir(directory):
        logger.error(f"ディレクトリが存在しません: {directory}")
        return

    logger.info(f"ディレクトリ内ノートブック翻訳開始: {directory}")
    for filename in os.listdir(directory):
        if filename.endswith('.ipynb'):
            input_path = os.path.join(directory, filename)
            translate_markdown_cells(input_path)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Jupyter NotebookのMarkdownセルをGoogle公式APIで日本語翻訳"
    )
    parser.add_argument(
        'directory',
        type=str,
        help='翻訳対象のノートブックがあるディレクトリを指定'
    )
    args = parser.parse_args()

    translate_notebooks_in_directory(args.directory)
