class Thing:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return f'thing: a={self.a}, b={self.b}'


thing = Thing(1, 2)

print(str(thing))

x = []
x[2] = 'blah'

print(x)