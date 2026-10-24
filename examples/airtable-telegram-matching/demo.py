from src.matching import Matcher
m = Matcher()
for person, chat in [('fake-user-1','10001'), ('fake-user-2','10002')]:
    m.bind(person,chat,m.token(person))
for event, person, code in [('evt-1','fake-user-1','DEMO-111'),('evt-1','fake-user-1','DEMO-111'),('evt-2','fake-user-2','DEMO-222')]:
    print(event, 'queued' if m.deliver(event,person,code) else 'duplicate skipped')
print('Simulated outbox:',m.outbox)
