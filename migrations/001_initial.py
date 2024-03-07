from settings import settings
from data import seconds_to_hms, Period, TimerDB


def migration_up():
    db = TimerDB()
    con = db.get_connection()
    con.execute('''
        DROP TABLE IF EXISTS period
    ''')
    con.execute('''
    CREATE TABLE period (
        time_start FLOAT PRIMARY KEY,
        time_end FLOAT,
        hours INT,
        minutes INT,
        seconds INT,
        comment VARCHAR(127)
    ) 
    ''')
    con.commit()


migration_up()
