import pronotepy
from pronotepy.ent import ile_de_france
from apiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from apscheduler.schedulers.background import BackgroundScheduler
from pymstodo import ToDoConnection
from config import session, Config
import pickle
from datetime import *
import os
import requests
import json
import time
import codecs


jourSemaine = ("Lundi", "Mardi", "Mercredi", "Jeudi",
               "Vendredi", "Samedi", "Dimanche")

# déclaration des variables globales
usernameENT = os.environ['USERNAME_ENT']
mdpENT = os.environ['PASSWORD_ENT']
tokenPushBullet = os.environ['TOKEN_PUSHBULLET']
calendar_id = os.environ['CALENDAR_ID']
listeToDo = os.environ['NAME_MICROSOFT_TODO_LIST']

# correspondance entre les couleurs de Pronote et de Google
colors = json.loads(os.environ['COLORS'])
# {"#F2ED82": 2, "#FD0222": 11, "#AFDEF9": 7, "#7CB927": 10, "#ED679B": 3, "#6ACAF2": 9, "#212853": 6, "#C0C0C0": 8, "#FFFF00": 5, "#A49E6C": 4, "#144897": 1}

service = None
client = None
todo_client = None


def connectGoogle():
    # connexion à l'api Google Calendar
    global service
    service = build("calendar", "v3", credentials=credentials)


def connectPronote():
    # connexion à l'api Pronote
    global client
    client = pronotepy.Client('https://0910626l.index-education.net/pronote/eleve.html',
                              username=usernameENT,
                              password=mdpENT,
                              ent=ile_de_france)


def connectTodo():
    # connexion à l'api ToDo
    global todo_client
    todo_client._refresh_token()


def notify(title, body):
    # prend en paramètre le title et le body et envoi une notification
    msg = {"type": "note", "title": title, "body": body}
    resp = requests.post('https://api.pushbullet.com/v2/pushes',
                         data=json.dumps(msg),
                         headers={'Authorization': 'Bearer ' + tokenPushBullet,
                                  'Content-Type': 'application/json'})
    if resp.status_code != 200:
        print('Error', resp.status_code)


def coursToAgenda():
    # récupère les cours sur Pronote et créé un event sur Google Calendar
    connectPronote()
    connectGoogle()
    # verifie si le client est connecté
    if client.logged_in:
        for i in range(1, 7):
            cours = client.lessons(date.today() + timedelta(days=i))
            for i in cours:
                # verifie si le prof n' est pas absent ou si le cours n'est pas annulé
                if (i.canceled != True and i.exempted != True) or len(i.virtual_classrooms) == 1:
                    start_time = i.start
                    end_time = i.end
                    timezone = 'Europe/Paris'
                    cours = i.subject.name
                    prof = i.teacher_name
                    if len(i.virtual_classrooms) == 1:
                        salle = i.virtual_classrooms[0]
                    else:
                        salle = i.classroom
                    if i.background_color in colors:
                        couleur = colors[i.background_color]
                    else:
                        couleur = '0'
                    id = i.teacher_name[0:3] + i.subject.name[0:4] + \
                        i.classroom[0:3] + \
                        start_time.strftime("%Y-%m-%dT%H:%M:%S")

                    event = {
                        'summary': cours,
                        'location': salle,
                        'description': prof,
                        'iCalUID': id,
                        'start': {
                            'dateTime': start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                            'timeZone': timezone,
                        },
                        'end': {
                            'dateTime': end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                            'timeZone': timezone,
                        },
                        'reminders': {
                            'useDefault': True,
                        },
                        'colorId': couleur
                    }
                    try:
                        # creer l'evenement
                        service.events().insert(
                            calendarId=calendar_id, body=event).execute()
                    except:
                        pass
                # envoi une notification sinon
                else:
                    notify(
                        'Cours annulé', f'Le cours de {i.subject.name} est annulé {jourSemaine[i.start.weekday()]} {i.start.day}/{i.start.month}')
    else:
        print('no login')


def verifAgenda():
    # récupère les cours sur Pronote et créé un event sur Google Calendar
    connectGoogle()
    # verifie si le client est connecté
    if client.logged_in:
        for i in range(0, 3):
            cours = client.lessons(date.today() + timedelta(days=i))
            for i in cours:
                start_time = i.start
                cours = i.subject.name
                prof = i.teacher_name
                if len(i.virtual_classrooms) == 1:
                    salle = i.virtual_classrooms[0]
                else:
                    salle = i.classroom
                id = i.teacher_name[0:3] + i.subject.name[0:4] + \
                    i.classroom[0:3] + start_time.strftime("%Y-%m-%dT%H:%M:%S")
                # verifie si le prof est absent ou si le cours est annulé
                if (i.canceled == True or i.exempted == True) and len(i.virtual_classrooms) == 0:
                    event = service.events().list(calendarId=calendar_id,
                                                  iCalUID=id).execute()
                    # verifie si l'evenement existe
                    if len(event['items']) == 1:
                        # supprime l'evenement
                        service.events().delete(calendarId=calendar_id,
                                                eventId=event['items'][0]['id']).execute()
                        notify(
                            'Cours annulé', f'Le cours de {i.subject.name} est annulé {jourSemaine[start_time.weekday()]}')
                else:
                    event = service.events().list(calendarId=calendar_id,
                                                  iCalUID=id).execute()
                    # verifie si l'evenement n'existe pas
                    if len(event['items']) == 0:
                        end_time = i.end
                        timezone = 'Europe/Paris'
                        if i.background_color in colors:
                            couleur = colors[i.background_color]
                        else:
                            couleur = '0'
                        event = {
                            'summary': cours,
                            'location': salle,
                            'description': prof,
                            'iCalUID': id,
                            'start': {
                                'dateTime': start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                                'timeZone': timezone,
                            },
                            'end': {
                                'dateTime': end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                                'timeZone': timezone,
                            },
                            'reminders': {
                                'useDefault': False,
                                'overrides': [
                                    {'method': 'popup', 'minutes': 10},
                                ],
                            },
                            'colorId': couleur
                        }
                        try:
                            # créé l'evenement
                            service.events().insert(
                                calendarId=calendar_id, body=event).execute()
                        except:
                            pass
    else:
        print('no login')


def notifNotes():
    # envoi une notification si il y a une nouvelle note
    # charge le fichier avec les notes deja envoyé
    lineNot = session.query(Config).one()
    if lineNot.notes != None:
        notes = json.loads(lineNot.notes)
    else:
        notes = []
    if client.logged_in:
        # récupère les notes
        period = client.current_period
        for grade in period.grades:
            id = grade.grade + \
                grade.subject.name[0:3] + grade.comment[0:4] + \
                str(grade.date.day) + str(grade.date.month)
            # verifie si une notification n'a pas déjà été envoyer pour cette note
            if id not in notes:
                notify(grade.subject.name + ' : ' + f'{grade.grade}/{grade.out_of}', 'Tu as eu ' + f'{grade.grade}/{grade.out_of}' +
                       ' en ' + grade.subject.name + ' sur ' + grade.comment + '\nMoyenne générale : ' + period.overall_average)
                notes.append(id)
        line.notes = json.dumps(notes)
        session.commit()


def todo():
    # met les devoirs dans ToDo
    connectTodo()
    connectPronote()
    # charge le fichier avec les devoirs deja ajouté
    lineDev = session.query(Config).one()
    if lineDev.devoirs != None:
        devoirs = json.loads(lineDev.devoirs)
    else:
        devoirs = []
    # récupère la liste todo dans laquelle il faut mettre les devoirs
    lists = todo_client.get_lists()
    for list in lists:
        if list.displayName == listeToDo:
            task_list = list
            break
    homeworks = client.homework(
        date.today(), date.today() + timedelta(days=30))
    for homework in homeworks:
        id = homework.description[0:10] + \
            homework.date.strftime("%Y-%m-%dT%H:%M:%S")
        if homework.done == False and id not in devoirs:
            todo_client.create_task(
                title=f'{homework.subject.name} {homework.description[0:100]}', list_id=task_list.list_id, due_date=homework.date, body_text=homework.description)
            devoirs.append(id)
    line.devoirs = json.dumps(devoirs)
    session.commit()


def sched():
    connectPronote()
    verifAgenda()
    notifNotes()


# true si le script n'est pas executé depuis un autre
if __name__ == "__main__":
    while session.query(Config).count() == 0:
        print('Please do the configuration with "python config.py"')
        time.sleep(60)

    line = session.query(Config).one()

    credentials = pickle.loads(codecs.decode(
        line.token_google.encode(), "base64"))
    todo_client = pickle.loads(codecs.decode(
        line.token_todo.encode(), "base64"))

    # todo()
    sched()
    scheduler = BackgroundScheduler()
    scheduler.add_job(coursToAgenda, 'cron',
                      day_of_week='sun', hour='17', minute='00')
    scheduler.add_job(sched, 'interval', minutes=30)
    scheduler.start()
    print("I'm working")
    # permet de garder l'application ouverte en permanence
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
