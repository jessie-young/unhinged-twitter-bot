import lancedb
# import pandas as pd
# import pyarrow as pa
import daft
import pandas as pd

uri = "./data/lancedb"
db = lancedb.connect(uri)

df = pd.DataFrame(
    [
        {"vector": [3.1, 4.1], "item": "foo", "price": 10.0},
        {"vector": [5.9, 26.5], "item": "bar", "price": 20.0},
    ]
)
df_csv = pd.read_csv('./data/datasets/twitter_dataset.csv')

tbl = db.create_table("table_from_df", data=df_csv)

df = daft.read_lance(url="./data/lancedb/table_from_df.lance")

df.show()