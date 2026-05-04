import discord
from discord.ext import commands
from discord.ui import View, Button

import requests
import json
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request, send_file

import io
import os
import datetime



description = '''Bot meant to help students with their schedules collaboratively'''

# Sets up the bot to work with the discord API
intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True
map = {}


bot = commands.Bot(command_prefix='!', description=description, intents=intents)



# This function is called when the bot is ready to be used
@bot.event
async def on_ready():
    # Shows that the bot is logged in
    global map
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')  
    fileReader = ""
    map = {}
    # Reads the file to get the map from the JSON file
    try:
        fileReader = open("data.json", "r")
        read = fileReader.read()
        map = json.loads(read)
        fileReader.close()
    except:
        print("File does not exist")
    # Sets the bot's status
    await bot.change_presence(status=discord.Status.offline, activity=discord.Game("Doing stuff"))
    
    synced = await bot.tree.sync()   
    
# This command prints the map, for debugging purposes
@bot.command(description="Prints the map")
async def printMap(ctx):
    await ctx.send(map)

# This command clears the map, for debugging purposes
@bot.command(description="Clears the map")
async def clear(ctx):
    # Checks if the user is the owner of the bot
    if ctx.author.id != 523309470105993226:
        await ctx.send("You do not have permission to clear the map")
        return
    else:
        # Clears the map and sets it to be empty, then writes it to the file
        global map
        # Clears the map by writing nothing to it
        writer = open("data.json", "w")
        writer.write("")
        writer.close()
        map = {}
        await ctx.send("Map cleared")


# This command clears the schedule of the user specified    
@bot.hybrid_command(name='clear_schedule', with_app_command=True)
async def clearSchedule(ctx):
    idString = f'{ctx.author.id}'
    map[idString] = {}
    f = open("data.json", "w")
    string = json.dumps(map)
    f.write(string)
    f.close()
    await ctx.send("Schedule cleared")


# This command adds a course to the user's schedule
@bot.hybrid_command(name = "add_course", description = "experiment")
async def addCourse(ctx,course,section):
    # Tries to add the course to the user's schedule
    try:
        # Checks if the user is in the map, if not, adds them
        idString = f'{ctx.author.id}'
        # If the user is not in the map, add them
        if idString not in map:
            map[f'{ctx.author.id}'] = {}
        url = f'https://api.umd.io/v1/courses/{course}'
        response = requests.get(url)
        data = response.json()
        # Checks if the course is valid
        if response.status_code != 200:
            await ctx.send("Invalid course")
            return
        url = f'https://api.umd.io/v1/courses/{course}/sections/{section}'
        response = requests.get(url)
        data = response.json()
        # Checks if the section is valid
        if response.status_code != 200:
            await ctx.send("Invalid section!")
            return

        # Adds the course to the user's schedule
        # by adding the course and section to the map
        tempMap = map[idString]
        tempMap[course.upper()]=section 
        writer = open("data.json", "w")
        string = json.dumps(map)
        writer.write(string)
        writer.close()
        # Sends a message to the user that the course was added
        await ctx.send(f"Course {course.upper()} added with section {section}")
    # If there is an error, sends a message to the user
    except:
        await ctx.send("Error adding course")

# This command displays a specific course
@bot.hybrid_command(name='course', with_app_command=True)
async def course(ctx, message: str):
    
    # Writes the map to the file   
    writer = open("data.json", "w")
    string = json.dumps(map)
    writer.write(string)
    writer.close()
    # Tries to get the course information
    try:
        url = f'https://api.umd.io/v1/courses/{message}'
        response = requests.get(url)
        data = response.json()
        text = ""
        info = ""
        # Gets the course information by breaking down the json file into pieces
        for course in data:
                info+=(f"{course['course_id']:}-")
                info+= (f"{course['name']}\n")
                text+=(f"Credits: {course['credits']}\n")
                text+=(f"Description {course['description']}\n")
                # Gets the prerequisites of the course
                relation = course['relationships']
                #Further breaks down the json file to get the prerequisites
                text+=(f"Prereq:  {relation['prereqs']}\n")
        embed= discord.Embed(title=info,description=text)
    except Exception :
        embed = discord.Embed(title="Invalid Course", description=f"Example of valid course, CMSC131, cmsc131 \nExample of Invalid course name, CMSC 131, CMSC1")
    await ctx.send(embed=embed)

# This command displays the sections of a course    
@bot.hybrid_command(name='section', with_app_command=True)
async def section(ctx,message):
    # Gets the sections of the course
    await ctx.defer()
    url = f'https://api.umd.io/v1/courses/{message}/sections'
    response = requests.get(url)
    data = response.json()
    text=""
    
    # Breaks down the json file to get the sections
    for course in data:
        text+=f"Course: {course['course']}\n"
        text+=f"Section Number: {course['number']}\n"
        text+=f"Total Seats: {course['seats']}\n"
        text+=f"Open Seats: {course['open_seats']}\n"
        text+=f"Professor: {course['instructors']}\n"
        # Further breaks it down to get meeting times

        for timing in course['meetings']:
            text+=f"Days: {timing['days']}\n"
            text+=f"Start Time: {timing['start_time']}\n"
        if(len(text)>1500):
            text+="\n"
            await ctx.send(text)
            text=""
        else:
            text+="\n"
    # Sends the message to the user to prevent overflow        
    if(len(text)>0):
        await ctx.send(text)
# This command displays the user's schedule and all courses        
@bot.hybrid_command(name='displayperson')
async def display_person(ctx, id):

    # Gets rid of the first few characters of the id
    course = map[id[2:len(id)-1]]
    text = ""
    credits = 0
    courseNames = []
    courses = []

    await ctx.defer()
    class MyView(discord.ui.View): 
        curr = 0
        def __init__(self):
            super().__init__()
            self.curr = 0
        def inc(self):
            self.curr+=1
        def dec(self):
            self.curr-=1
        @discord.ui.button(label='↩', style=discord.ButtonStyle.primary)
        async def left(self, interaction: discord.Interaction, button: discord.Button):
            try:
                self.dec()
                while self.curr<0:
                    self.curr+=len(courses)
                embed= discord.Embed(title=courseNames[self.curr%len(courses)],description=courses[self.curr%len(courses)])
                await interaction.response.edit_message(embed=embed)
            except Exception as e:
                if interaction.response.is_done():
                    await interaction.followup.send(e)
                else:
                    await interaction.response.send_message(e)
        @discord.ui.button(label='↪', style=discord.ButtonStyle.primary)
        async def right(self, interaction: discord.Interaction, button: discord.Button):
            try:
                self.inc()
                while self.curr<0:
                    self.curr+=len(courses)
                embed= discord.Embed(title=courseNames[self.curr%len(courses)],description=courses[self.curr%len(courses)])
                await interaction.response.edit_message(embed=embed)
            except Exception as e:
                if interaction.response.is_done():
                    await interaction.followup.send(e)
                else:
                    await interaction.response.send_message(e)           
    try:
        # Gets the course information from the name and ID
        for key in course:
            courseLink = f'https://api.umd.io/v1/courses/{key}'
            sectionLink = f'https://api.umd.io/v1/courses/{key}/sections/{course[key]}'
            section_response = requests.get(sectionLink)
            course_response = requests.get(courseLink)
            course_data = course_response.json()
            section_data = section_response.json()
            
            courseName = key
            courseSection = course[key]
            for datum in course_data:
                text+=f"Credit: {datum['credits']}\n"
                credits+=int(datum['credits'])
            text+=f"Section: {courseSection}\n"
            
            # Breaks down the json file to get the course information
            for datam in section_data:
                if(datam['instructors']==[]):
                    text+="Instructors: TBA\n"
                else:
                    instructor =datam['instructors']
                    text+='Instructors: '
                    for inst in instructor:
                        text+=f"{inst} AND/OR " 
                    text = text[0:-7] + "\n"   
                 

                # Further breaks down the json file to get the professor and times
                for times in datam['meetings']:
                    text+=f"Meeting: {times['days']}\n"
                    text+=f"Class Time: {times['start_time']}\n"
                text+="\n"
            courses.append(text) 
            courseNames.append(courseName)
            text = ""

        text+=f"{credits} credits\n"
        view = MyView()
        if(len(courses)>0):
            embed = discord.Embed(title=courseNames[0], description=courses[0])
            await ctx.send(embed=embed, view=view)

        else:
            await ctx.send("No courses found")
    except Exception as e:
        print(e)
        await ctx.send("No courses found")  
        
@bot.hybrid_command(name='display')
async def display(ctx):
    await display_person(ctx, str(f'<@{ctx.author.id}>'))
        
# This command tests an embed
@bot.command()
async def embed(ctx):
    embed= discord.Embed(title="Sample")
    await ctx.send(embed=embed)
    
# This command changes the ID of the bot, for debugging purposes
@bot.command()
async def changeId(ctx, id : int):
    await ctx.send(f'ID is now {id}')

@bot.hybrid_command()
async def compare_schedules(ctx, id1 : str):
    user1 = map[id1[2:len(id1)-1]]
    id2 = str(f'<@{ctx.author.id}>')
    user2 = map[id2[2:len(id2)-1]]
    a = set(user1.keys())
    b = set(user2.keys())
    common = a.intersection(b)
    text = "Classes in common:\n"
    for parts in common:
        text+=f"{parts}\n"
    if(text=="Classes in common:\n"):
        text = "No classes in common"
    await ctx.send(text)    

    combinedList = []
    text = "Sections in common:\n"
    for parts in common:

        if user1[parts] == user2[parts]:
            text+=f"{parts} {user1[parts]}\n"
            
    if(text=="Sections in common:\n"):
        text = "No sections in common"
    await ctx.send(text)        


@bot.hybrid_command()
async def compute_avg(ctx):
    id = str(f'<@{ctx.author.id}>')
    user = map[id[2:len(id)-1]]
    credit = 0.0
    grade = 0.0
    display = "Average Grades according to PlanetTerp:\n"
    text = ""
    for key in user:
        link = f'https://planetterp.com/api/v1/course?name={key}'
        response = requests.get(link)
        data = response.json()
        text += f"{data['name']}: {round(data['average_gpa'], 3)}, {await compute(data)} Credits\n"

        credit += await compute(data)
    if(credit==0.0):
        await ctx.send("No courses found")
    else:
        text+=f"Average GPA: {round(grade/credit,3)}, {credit} Credits"
        
        embed = discord.Embed(title=display, description=text)
        await ctx.send(embed=embed) 


async def compute(data):
    credit = 0.0
    try:
        credit+=(data['credits'])
    except:
        credit+=3.0
    return credit


@bot.hybrid_command()
async def remove_course(ctx,course):

    id = str(f'<@{ctx.author.id}>')
    user = map[id[2:len(id)-1]]

    if course in user:
        user.pop(course)
        await ctx.send(f"{course} removed")

    else:
        await ctx.send("Course not in the database")
    r = open("data.json", "w")
    r.write(json.dumps(map))   
    r.close() 


async def sch(ctx):
    schedule = {"M": {}, "Tu": {}, "W": {}, "Th": {}, "F": {}}
    users = str(f'{ctx.author.id}')
    users = map[users]
    for key in users:
        days = []
        link = f'https://api.umd.io/v1/courses/{key}/sections/{users[key]}'
        response = requests.get(link)
        data = response.json()
        for datum in data:
            for times in datum['meetings']:
                for i in range(len(times['days'])):
                    if(times['days'][i] == 'h' or times['days'][i] == 'u') :
                        continue
                    if times['days'][i] == 'T':
                        if times['days'][i+1] == 'u':
                            days.append("Tu")
                            schedule["Tu"][times['start_time']] = key
                        else:
                            days.append("Th")    
                            schedule["Th"][times['start_time']] = key
                    else:
                        days.append(times['days'][i])
                        schedule[times['days'][i]][times['start_time']] = key              
    return schedule   
       
import matplotlib.pyplot as plt
import io
schedule = {"Monday": ["CMSC131", "CMSC132", "CMSC216"], "Tuesday": ["CMSC131", "CMSC132", "CMSC216"], "Wednesday": ["CMSC131", "CMSC132", "CMSC216"], "Thursday": ["CMSC131", "CMSC132", "CMSC216"], "Friday": ["CMSC131", "CMSC132", "CMSC216"]}

async def draw_schedule(ctx):
    schedule_list = await sch(ctx)
    print(schedule_list)
    days = ["Mon", "Tues", "Wed", "Thurs", "Fri"]
    #indexX = {"M" : 1 , "Tu" : 2, "W" : 3, "Th" : 4, "F" : 5}
    indexX = {1: "M", 2: "Tu", 3: "W", 4: "Th", 5: "F"}
    indexY = {}
    for i in range(8, 100):
        indexY[i] = i - 7
    #indexY = {8: 1, 9: 2, 10: 3, 11: 4, 12: 5, 13: 6, 14: 7, 15: 8, 16: 9, 17: 10,18:11,19:12,20:13,21:14,22:15,23:16,24:17,25:18,26:19,27:20,28:21}
    
    # Include :30 times for each hour
    hours = [f"{hour}:00" for hour in range(8, 18)] + [f"{hour}:30" for hour in range(8, 17)]
    hours.sort(key=lambda time: int(time.split(':')[0]) * 60 + int(time.split(':')[1]))  # Sort times

    fig, ax = plt.subplots()
    ax.axis('off')
    table_data = []

    # Prepare table data
    for hour in hours:
        hour_schedule = [hour]
        for day in days:
            day_schedule = schedule.get(day, [])
            subject_at_hour = ""
            for time_slot in day_schedule:
                if " - " in time_slot:
                    time, subject = time_slot.split(" - ")
                    if time == hour:
                        subject_at_hour = subject
                        break
            hour_schedule.append(subject_at_hour)
        table_data.append(hour_schedule)
        
    # Create table
    table = ax.table(cellText=table_data, colLabels=["Time"] + days, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    for i in range(1, 6):
        for j in schedule_list[indexX[i]]: 
            if str(j[-2:]) == 'pm':
                y = int(indexY[(12 + int(j[0:-5]))]) 
            else: 
                y = int(indexY[int(j[0:-5])])
            if(j[-2:] == 'pm' and j[0:-5] == '12'):
                y-=12
            if(j[-4:-2] == '30'):
                y+=.5
            table[(2*y -1, i)].set_text_props(text=schedule_list[indexX[i]][j]) 
            cell = table[(2*y -1 , i)] 
            cell.set_facecolor('yellow')
    
    table.set_fontsize(14)
    table.scale(1.2, 1.25)

    # Save figure to a BytesIO buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    return buf


@bot.hybrid_command(name='schedule')
async def schedule_command(ctx):
    print("Drawing schedule")
    buf = await draw_schedule(ctx)
    file = discord.File(fp=buf, filename='schedule.png')
    await ctx.send("Here is the weekly schedule:", file=file)
bot.run(os.getenv("DISCORD_TOKEN"))
