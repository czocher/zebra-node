import sys
x, y = raw_input().split()
for n in range(int(x), int(y) + 1):
    sys.stdout.write(str(n))
    sys.stdout.write(' ')
sys.stdout.write('\n')
