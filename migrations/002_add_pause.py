from data import seconds_to_hms, Period, TimerDB

def migration_up():
    db = TimerDB()
    con = db.get_connection()
    con.execute('''
        ALTER TABLE period
        ADD COLUMN pause_time float DEFAULT 0 NOT NULL
    ''')
    con.commit()


migration_up()
