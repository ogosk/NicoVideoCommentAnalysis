PYTHON_LIB_DIR=`python -c "import site; print(site.getsitepackages()[0])"`
SUDACHIDICT_TYPE="small"

pyinstaller nvca.py \
    --clean \
    --noconfirm \
    --noconsole \
    --add-data="${PYTHON_LIB_DIR}/wordcloud/stopwords:wordcloud" \
    --add-data="${PYTHON_LIB_DIR}/sudachipy/resources:sudachipy/resources" \
    --add-data="${PYTHON_LIB_DIR}/sudachidict_${SUDACHIDICT_TYPE}/resources/system.dic:sudachipy/resources" \
    --add-data="./data/sudachi.json:sudachipy/resources" \
    --add-data="./data/chr.yaml:data" \
    --add-data="./data/exclude_noun.yaml:data" \
