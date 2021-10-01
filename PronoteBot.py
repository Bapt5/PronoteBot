import pronotepy
from apiclient.discovery import build
from apscheduler.schedulers.blocking import BlockingScheduler
from PIL.ImageColor import getrgb
from skimage import color as cl
from math import sqrt
from config import session, Config
from ENTs import ents
from datetime import *
import pickle
import requests
import json
import time
import codecs

jourSemaine = ("Lundi", "Mardi", "Mercredi", "Jeudi",
               "Vendredi", "Samedi", "Dimanche")


class PronoteBot:
    def __init__(self,
                 urlPronote,
                 usernamePronote,
                 mdpPronote,
                 ent,
                 tokenPushBullet,
                 calendar_id,
                 listeToDo):
        # déclaration des variables globales
        self.urlPronote = urlPronote
        self.usernamePronote = usernamePronote
        self.mdpPronote = mdpPronote
        self.ent = ents.get(ent)
        self.tokenPushBullet = tokenPushBullet
        self.calendar_id = calendar_id
        self.listeToDo = listeToDo

        self.credentialsGoogle = None
        self.service = None
        self.client = None
        self.todo_client = None

    def run(self):
        self.line = session.query(Config).one()

        self.credentialsGoogle = pickle.loads(codecs.decode(
            self.line.token_google.encode(), "base64"))
        self.todo_client = pickle.loads(codecs.decode(
            self.line.token_todo.encode(), "base64"))

        self.client = pronotepy.Client(self.urlPronote,
                                       username=self.usernamePronote,
                                       password=self.mdpPronote,
                                       ent=self.ent)
        self.sched()
        scheduler = BlockingScheduler()
        scheduler.add_job(self.coursToAgenda, 'cron',
                          day_of_week='sun', hour='17', minute='00')
        scheduler.add_job(self.sched, 'interval', minutes=30)
        print("I'm working")
        scheduler.start()

    def sched(self):
        self.client.session_check()
        self.verifAgenda()
        self.notifNotes()
        self.todo()

    def connectGoogle(self):
        if self.credentialsGoogle and self.calendar_id:
            # connexion à l'api Google Calendar
            self.service = build(
                "calendar", "v3", credentials=self.credentialsGoogle)

    def connectTodo(self):
        if self.todo_client and self.listeToDo:
            # connexion à l'api ToDo
            self.todo_client._refresh_token()

    def notify(self, title, body):
        if self.tokenPushBullet:
            # prend en paramètre le title et le body et envoi une notification
            msg = {"type": "note", "title": title, "body": body}
            resp = requests.post('https://api.pushbullet.com/v2/pushes',
                                 data=json.dumps(msg),
                                 headers={'Authorization': 'Bearer ' + self.tokenPushBullet,
                                          'Content-Type': 'application/json'})
            if resp.status_code != 200:
                print('Error', resp.status_code)
        else:
            print("You don't want to use Pushbullet for notifications")

    @staticmethod
    def convertColor(color):
        color = cl.rgb2lab(getrgb(color))
        colorIds = {
            '#7986cb': 1,
            '#33b679': 2,
            '#8e24aa': 3,
            '#e67c73': 4,
            '#f6c026': 5,
            '#f5511d': 6,
            '#039be5': 7,
            '#616161': 8,
            '#3f51b5': 9,
            '#0b8043': 10,
            '#d60000': 11
        }
        distances = []
        for colorId, id in colorIds.items():
            colorIdLab = cl.rgb2lab(getrgb(colorId))
            distances.append((sqrt((color[0] - colorIdLab[0])**2 + (
                color[1] - colorIdLab[1]) ** 2 + (color[2] - colorIdLab[2])**2), id))
        return min(distances)[1]

    def coursToAgenda(self):
        # récupère les cours sur Pronote et créé un event sur Google Calendar
        self.client.session_check()
        self.connectGoogle()
        # verifie si le client est connecté
        if self.client.logged_in and self.credentialsGoogle and self.calendar_id:
            for i in range(1, 7):
                cours = self.client.lessons(date.today() + timedelta(days=i))
                for cour in cours:
                    # verifie si le prof n' est pas absent ou si le cours n'est pas annulé
                    if (cour.canceled != True and cour.exempted != True) or len(cour.virtual_classrooms) == 1:
                        start_time = cour.start
                        end_time = cour.end
                        timezone = 'Europe/Paris'
                        cours = cour.subject.name
                        prof = cour.teacher_name
                        if len(cour.virtual_classrooms) == 1:
                            salle = cour.virtual_classrooms[0]
                        else:
                            if cour.classroom:
                                salle = cour.classroom
                            else:
                                salle = ''
                        id = cour.teacher_name[0:3] + cour.subject.name[0:4] + \
                            salle[0:3] + \
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
                            'colorId': self.convertColor(cour.background_color)
                        }
                        try:
                            # creer l'evenement
                            self.service.events().insert(
                                calendarId=self.calendar_id, body=event).execute()
                        except:
                            pass
                    # envoi une notification sinon
                    else:
                        self.notify(
                            'Cours annulé', f'Le cours de {cour.subject.name} est annulé {jourSemaine[cour.start.weekday()]} {cour.start.day}/{cour.start.month}')
        else:
            print('no login')

    def verifAgenda(self):
        # récupère les cours sur Pronote et créé un event sur Google Calendar
        self.connectGoogle()
        # verifie si le client est connecté
        if self.client.logged_in and self.credentialsGoogle and self.calendar_id:
            for i in range(0, 3):
                cours = self.client.lessons(date.today() + timedelta(days=i))
                for cour in cours:
                    start_time = cour.start
                    cours = cour.subject.name
                    prof = cour.teacher_name
                    if len(cour.virtual_classrooms) == 1:
                        salle = cour.virtual_classrooms[0]
                    else:
                        if cour.classroom:
                            salle = cour.classroom
                        else:
                            salle = ''
                    id = cour.teacher_name[0:3] + cour.subject.name[0:4] + \
                        salle[0:3] + start_time.strftime("%Y-%m-%dT%H:%M:%S")
                    # verifie si le prof est absent ou si le cours est annulé
                    if (cour.canceled == True or cour.exempted == True) and len(cour.virtual_classrooms) == 0:
                        event = self.service.events().list(calendarId=self.calendar_id,
                                                           iCalUID=id).execute()
                        # verifie si l'evenement existe
                        if len(event['items']) == 1:
                            # supprime l'evenement
                            self.service.events().delete(calendarId=self.calendar_id,
                                                         eventId=event['items'][0]['id']).execute()
                            self.notify(
                                'Cours annulé', f'Le cours de {cour.subject.name} est annulé {jourSemaine[start_time.weekday()]}')
                    else:
                        event = self.service.events().list(calendarId=self.calendar_id,
                                                           iCalUID=id).execute()
                        # verifie si l'evenement n'existe pas
                        if len(event['items']) == 0:
                            end_time = cour.end
                            timezone = 'Europe/Paris'
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
                                'colorId': self.convertColor(cour.background_color)
                            }
                            try:
                                # créé l'evenement
                                self.service.events().insert(
                                    calendarId=self.calendar_id, body=event).execute()
                            except:
                                pass
        else:
            print('no login')

    def notifNotes(self):
        # envoi une notification si il y a une nouvelle note
        # charge le fichier avec les notes deja envoyé
        lineNot = session.query(Config).one()
        if lineNot.notes != None:
            notes = json.loads(lineNot.notes)
        else:
            notes = []
        if self.client.logged_in and self.tokenPushBullet:
            # récupère les notes
            period = self.client.current_period
            for grade in period.grades:
                id = grade.grade + \
                    grade.subject.name[0:3] + grade.comment[0:4] + \
                    str(grade.date.day) + str(grade.date.month)
                # verifie si une notification n'a pas déjà été envoyer pour cette note
                if id not in notes:
                    self.notify(f'{grade.subject.name} : {str(grade.grade)}/{str(grade.out_of)}', f'Tu as eu {str(grade.grade)} / {str(grade.out_of)} en {grade.subject.name} sur {grade.comment}\nMoyenne générale: {period.overall_average}')
                    notes.append(id)
            self.line.notes = json.dumps(notes)
            session.commit()

    def todo(self):
        # met les devoirs dans ToDo
        self.connectTodo()
        # charge le fichier avec les devoirs deja ajouté
        lineDev = session.query(Config).one()
        if lineDev.devoirs != None:
            devoirs = json.loads(lineDev.devoirs)
        else:
            devoirs = []
        if self.client.logged_in and self.todo_client and self.listeToDo:
            # récupère la liste todo dans laquelle il faut mettre les devoirs
            lists = self.todo_client.get_lists()
            task_list = None
            for list in lists:
                if list.displayName == self.listeToDo:
                    task_list = list
                    break
            if task_list == None:
                self.todo_client.create_list(name=self.listeToDo)
            # récupére tous les devoirs pour les 30 prochains jours
            homeworks = self.client.homework(
                date.today(), date.today() + timedelta(days=30))
            for homework in homeworks:
                # création de l'id
                id = homework.description[0:10] + \
                    homework.date.strftime("%Y-%m-%dT%H:%M:%S")
                # si le devoir n'est pas fini est qu'il n'est pas encore dans todo on l'ajoute
                if homework.done == False and id not in devoirs:
                    self.todo_client.create_task(
                        title=f'{homework.subject.name[0:5]} {homework.description[0:100]}', list_id=task_list.list_id, due_date=homework.date, body_text=f'{homework.subject.name} : {homework.description}')
                    devoirs.append(id)
                # Si il est fait on le coche sur todo
                else:
                    tasks = self.todo_client.get_tasks(
                        list_id=task_list.list_id, status='notCompleted')
                    for task in tasks:
                        if task.dueDateTime == homework.date and task.body == homework.description:
                            self.todo_client.complete_task(
                                task_id=task.task_id, list_id=task_list.list_id)
                            break
            # récupére tous les devoirs fait
            tasks = self.todo_client.get_tasks(
                list_id=task_list.list_id, status='completed')
            # on coche le devoirs sur pronote
            for task in tasks:
                homeworks = self.client.homework(
                    date.today(), date.today() + timedelta(days=30))
                for homework in homeworks:
                    if task.dueDateTime == homework.date and task.body == homework.description:
                        homework.set_done(status=True)

            self.line.devoirs = json.dumps(devoirs)
            session.commit()
