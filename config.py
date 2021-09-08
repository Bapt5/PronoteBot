from sqlalchemy import create_engine
from sqlalchemy import Table, Column, String, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from google_auth_oauthlib.flow import InstalledAppFlow
from pymstodo import ToDoConnection
import os
import codecs
import pickle


url = os.environ['DATABASE_URL'].replace('postgres', 'postgresql')

db = create_engine(url)
base = declarative_base()
Session = sessionmaker(db)
session = Session()


class Config(base):
    __tablename__ = 'config'

    token_google = Column(String, primary_key=True)
    token_todo = Column(String)
    devoirs = Column(String)
    notes = Column(String)


base.metadata.create_all(db)


if __name__ == '__main__':
    scopes = ['https://www.googleapis.com/auth/calendar']
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json", scopes=scopes)
    credentials = flow.run_console()
    tokenGoogle = codecs.encode(pickle.dumps(credentials), "base64").decode()

    # identifiant de connexion à l'app
    client_id = '7035ca26-c986-4bae-8b6b-f1db229e05c5'
    client_secret = 'HuN_p3_St9~7c36U4H4k8B0pjPEVdi_2bM'

    auth_url = ToDoConnection.get_auth_url(client_id)
    redirect_resp = input(
        f'Go to this link do all the steps:\n{auth_url}\n\nPaste the redirect link here\n')
    token = ToDoConnection.get_token(
        client_id, client_secret, redirect_resp)
    todo_client = ToDoConnection(
        client_id=client_id, client_secret=client_secret, token=token)
    tokenToDo = codecs.encode(pickle.dumps(todo_client), "base64").decode()

    if session.query(Config).count() == 0:
        line = Config(token_google=tokenGoogle,
                      token_todo=tokenToDo, devoirs=None, notes=None)
        session.add(line)
        session.commit()
    else:
        line = session.query(Config).one()
        line.token_google = tokenGoogle
        line.token_todo = tokenToDo
        session.commit()
    print('End of configuration')
