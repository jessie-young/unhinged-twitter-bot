import lancedb
# import pandas as pd
# import pyarrow as pa
import daft
import pandas as pd
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry


uri = "./data/lancedb"
db = lancedb.connect(uri)

func = get_registry().get("sentence-transformers").create(name="BAAI/bge-small-en-v1.5", device="cpu")
class Words(LanceModel):
    text: str = func.SourceField()
    vector: Vector(func.ndims()) = func.VectorField()

# df_csv = pd.read_csv('./data/datasets/twitter_dataset.csv')

df = daft.read_csv('./data/datasets/twitter_dataset.csv')

# Convert the 'Text' column to embeddings
# df_daft = df_daft.with_column("vector", func.embed(df_daft["Text"]))

# Create a LanceDB table with the embeddings and other metadata
table = db.create_table("tweets", schema=Words, mode="overwrite")
table.add([{"text": t["Text"]} for t in df.iter_rows()])

results = (
    table.search("business")
        .limit(10)
        .to_pandas()
)

print(results)
# query = "greetings"
# actual = table.search(query).limit(1).to_pydantic(Words)[0]
# print(actual.text)


# df = daft.read_lance(url="./data/lancedb/tweets.lance")

# df.show()

