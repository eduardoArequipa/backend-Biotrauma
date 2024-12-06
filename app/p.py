import bcrypt
hashed = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
print("hola")
print(hashed)