from sqlalchemy import create_engine
import pandas as pd

def upload_to_mysql(df: pd.DataFrame, user, password, host, port, database, table):
    engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
    with engine.connect() as conn:
        df.to_sql(table, con=conn, if_exists="replace", index=False)
