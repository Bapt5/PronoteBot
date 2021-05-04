from pymstodo import ToDoConnection
import os
import pickle
import datetime

client_id = '7035ca26-c986-4bae-8b6b-f1db229e05c5'
client_secret = 'HuN_p3_St9~7c36U4H4k8B0pjPEVdi_2bM'

if os.path.isfile("toDo.pkl"):
    todo_client = pickle.load(open("toDo.pkl", "rb"))
    todo_client._refresh_token()
else:
    auth_url = ToDoConnection.get_auth_url(client_id)
    redirect_resp = input(
        f'Va sur ce lien fait toutes les étapes:\n{auth_url}\n\nColle ici le lien vers lequel tu es redirigé:\n')
    token = ToDoConnection.get_token(client_id, client_secret, redirect_resp)
    todo_client = ToDoConnection(
        client_id=client_id, client_secret=client_secret, token=token)
    pickle.dump(todo_client, open("toDo.pkl", "wb"))

lists = todo_client.get_lists()
for list in lists:
    if list.displayName == '📕Devoirs':
        task_list = list
        break
tasks = todo_client.get_tasks(task_list.list_id)

print(task_list)
# todo_client.create_task('maths 3p57', task_list.list_id)
print(*tasks, sep='\n')
for task in tasks:
    print(task.task_id)
    print()
