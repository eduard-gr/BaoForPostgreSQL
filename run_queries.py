import psycopg2
import json
import os
import sys
import random
from time import time, sleep
import configparser

def read_config():
    config = configparser.ConfigParser()
    config.read("bao_server/bao.cfg")

    if "bao" not in config:
        print("bao.cfg does not have a [bao] section.")
        exit(-1)

    config = config["bao"]
    return config

config = read_config()

bao_port = int(config["Port"])
db_name = config["Database"]
password = config["Password"]

USE_BAO = True

PG_CONNECTION_STR = "dbname={} user=postgres password={} host=localhost".format(
    db_name,
    password)

# https://stackoverflow.com/questions/312443/
def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def run_query(sql, file_name, bao_select=False, bao_reward=False):
    start = time()

    try:
        conn = psycopg2.connect(PG_CONNECTION_STR)
        cur = conn.cursor()
        cur.execute(f"SET bao_port TO {bao_port}")
        cur.execute(f"SET enable_bao TO {bao_select or bao_reward}")
        cur.execute(f"SET enable_bao_selection TO {bao_select}")
        cur.execute(f"SET enable_bao_rewards TO {bao_reward}")
        cur.execute("SET bao_num_arms TO 5")
        cur.execute("SET statement_timeout TO 500000")

        metadata = {
            "dbname": db_name,
            "query_name": file_name,
            "bao_enabled": (bao_select or bao_reward),
            "bao_select": bao_select,
            "bao_reward": bao_reward,
        }

        cur.execute("/**{}**/{}".format(
            metadata,
            sql
        ))

        cur.fetchall()
        conn.close()
        #break
    except:
        return -1

    stop = time()
    return stop - start

        
query_paths = sys.argv[1:]
queries = []
for fp in query_paths:
    with open(fp) as f:
        query = f.read()
    queries.append((fp, query))
print("Read", len(queries), "queries.")
print("Using Bao:", USE_BAO)

random.seed(42)
query_sequence = random.choices(queries, k=500)
pg_chunks, *bao_chunks = list(chunks(query_sequence, 25))

print("Executing queries using PG optimizer for initial training")

for fp, q in pg_chunks:
    pg_time = run_query(q, fp, bao_reward=True)
    print("x", "x", time(), fp, pg_time, "PG", flush=True)

for c_idx, chunk in enumerate(bao_chunks):
    if USE_BAO:
        os.system("cd bao_server && python3 baoctl.py --retrain")
        os.system("sync")
    for q_idx, (fp, q) in enumerate(chunk):
        q_time = run_query(q, fp, bao_reward=USE_BAO, bao_select=USE_BAO)
        print(c_idx, q_idx, time(), fp, q_time, flush=True)
