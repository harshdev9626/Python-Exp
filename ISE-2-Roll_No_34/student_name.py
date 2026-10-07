#create a text file and write student names into it 
file =open("student.txt","w")
n=int(input("Enter Numbe of Student:"))
for i in range(n):
    name = input("Enter student name: ")
    file.write(name + "\n")
file.close()
print("Student names added successfully")