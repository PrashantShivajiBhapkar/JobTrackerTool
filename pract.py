import datetime

format = "%H:%M:%S %a, %b-%d-%Y"
print(datetime.datetime.strptime(datetime.datetime.today().strftime(format), format).strftime(format))
# print('strptime:', d.strftime(format))



print('--NOTE: All the following details are of those jobs that match at least {0}% '.format(1)+
        'with your profile in terms of skills and are no older than {0} days.'.format(5))


print('mac' in 'machine ')