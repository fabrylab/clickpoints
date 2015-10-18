# setup mysql for sql annotations 
from peewee import *
from datetime import datetime

class SQLAnnotation(Model):
        timestamp = DateTimeField()
        system = CharField()
        camera = CharField()
        tags =  CharField()
        rating = IntegerField()
        reffilename = CharField()
        reffileext = CharField()
        comment = TextField()
        fileid = IntegerField()

        class Meta:
            database = None
            

sql_annotation=True
sql_dbname='annotation'
sql_host='131.188.117.94'
sql_port=3306
sql_user = 'clickpoints'
sql_pwd = '123456'


          
 # init db connection
db = MySQLDatabase(sql_dbname,
                        host=sql_host,
                        port=sql_port,
                        user=sql_user,
                        passwd=sql_pwd)
# connect
db.connect()

# check connection state
if db.is_closed():
    print("Couldn't open connection to DB %s on host %s",sql_dbname,sql_host)
    # TODO clean break?
else:
    print("connection established")

# create table
db.create_table(SQLAnnotation)


