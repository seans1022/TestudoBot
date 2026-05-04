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
import asyncio
import matplotlib
# This forces Matplotlib to run in the background without a GUI
matplotlib.use('Agg') 
import matplotlib.pyplot as plt


description = '''Bot meant to help students with their schedules collaboratively'''

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True
map = {}


bot = commands.Bot(command_prefix='!', description=description, intents=intents)


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content.lower().split().count("idgaf")>0:
        await message.channel.send(message.content)
    await bot.process_commands(message)
    

@bot.event
async def on_ready():
    global map
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')  
    fileReader = ""
    map = {}
    try:
        fileReader = open("data.json", "r")
        read = fileReader.read()
        map = json.loads(read)
        fileReader.close()
    except:
        print("File does not exist")
    await bot.change_presence(status=discord.Status.offline, activity=discord.Game("Doing stuff"))
    
    synced = await bot.tree.sync()   
    
@bot.command(description="Prints the map")
async def printMap(ctx):
    await ctx.send(map)

@bot.command(description="Clears the map")
async def clear(ctx):
    if ctx.author.id != 523309470105993226:
        await ctx.send("You do not have permission to clear the map")
        return
    else:
        global map
        writer = open("data.json", "w")
        writer.write("")
        writer.close()
        map = {}
        await ctx.send("Map cleared")


@bot.hybrid_command(name='clear_schedule', with_app_command=True)
async def clearSchedule(ctx):
    idString = f'{ctx.author.id}'
    map[idString] = {}
    f = open("data.json", "w")
    string = json.dumps(map)
    f.write(string)
    f.close()
    await ctx.send("Schedule cleared")


@bot.hybrid_command(name = "add_course", description = "experiment")
async def addCourse(ctx,course,section):
    try:
        idString = f'{ctx.author.id}'
        if idString not in map:
            map[f'{ctx.author.id}'] = {}
        url = f'https://api.umd.io/v1/courses/{course}'
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200:
            await ctx.send("Invalid course")
            return
        url = f'https://api.umd.io/v1/courses/{course}/sections/{section}'
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200:
            await ctx.send("Invalid section!")
            return

        tempMap = map[idString]
        tempMap[course.upper()]=section 
        writer = open("data.json", "w")
        string = json.dumps(map)
        writer.write(string)
        writer.close()
        await ctx.send(f"Course {course.upper()} added with section {section}")
    except:
        await ctx.send("Error adding course")

@bot.hybrid_command(name='course', with_app_command=True)
async def course(ctx, message: str):
    
    writer = open("data.json", "w")
    string = json.dumps(map)
    writer.write(string)
    writer.close()
    try:
        url = f'https://api.umd.io/v1/courses/{message}'
        response = requests.get(url)
        data = response.json()
        text = ""
        info = ""
        for course in data:
                info+=(f"{course['course_id']:}-")
                info+= (f"{course['name']}\n")
                text+=(f"Credits: {course['credits']}\n")
                text+=(f"Description {course['description']}\n")
                relation = course['relationships']
                text+=(f"Prereq:  {relation['prereqs']}\n")
        embed= discord.Embed(title=info,description=text)
    except Exception :
        embed = discord.Embed(title="Invalid Course", description=f"Example of valid course, CMSC131, cmsc131 \nExample of Invalid course name, CMSC 131, CMSC1")
    await ctx.send(embed=embed)

@bot.hybrid_command(name='section', with_app_command=True)
async def section(ctx,message):
    await ctx.defer()
    url = f'https://api.umd.io/v1/courses/{message}/sections'
    response = requests.get(url)
    data = response.json()
    text=""
    
    for course in data:
        text+=f"Course: {course['course']}\n"
        text+=f"Section Number: {course['number']}\n"
        text+=f"Total Seats: {course['seats']}\n"
        text+=f"Open Seats: {course['open_seats']}\n"
        text+=f"Professor: {course['instructors']}\n"

        for timing in course['meetings']:
            text+=f"Days: {timing['days']}\n"
            text+=f"Start Time: {timing['start_time']}\n"
        if(len(text)>1500):
            text+="\n"
            await ctx.send(text)
            text=""
        else:
            text+="\n"
    if(len(text)>0):
        await ctx.send(text)

@bot.hybrid_command(name='displayperson')
async def display_person(ctx, id):

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
            
            for datam in section_data:
                if(datam['instructors']==[]):
                    text+="Instructors: TBA\n"
                else:
                    instructor =datam['instructors']
                    text+='Instructors: '
                    for inst in instructor:
                        text+=f"{inst} AND/OR " 
                    text = text[0:-7] + "\n"   
                 

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
        
@bot.command()
async def embed(ctx):
    embed= discord.Embed(title="Sample")
    await ctx.send(embed=embed)
    
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


def sch(user_id):
    schedule = {"M": [], "Tu": [], "W": [], "Th": [], "F": []}
    
    if user_id not in map:
        return schedule
        
    user_courses = map[user_id]
    headers = {"User-Agent": "TestudoBot/1.0"}
    
    for key in user_courses:
        section = str(user_courses[key]).strip().zfill(4)
        link = f'https://api.umd.io/v1/courses/{key}/sections/{section}'
        
        try:
            response = requests.get(link, headers=headers)
            
            if response.status_code != 200:
                print(f"Skipping {key} - API returned {response.status_code}")
                continue 
                
            data = response.json()
            
            if not isinstance(data, list): 
                continue
                
            for datum in data:
                for times in datum.get('meetings', []):
                    start = times.get('start_time')
                    end = times.get('end_time')
                    
                    if not start or not end:
                        continue
                        
                    days_str = times.get('days', '')
                    
                    i = 0
                    while i < len(days_str):
                        d = days_str[i]
                        if d in ['h', 'u', 'S', ' ']: 
                            i += 1
                            continue
                        
                        day_key = d
                        if d == 'T':
                            if i + 1 < len(days_str) and days_str[i+1] == 'u':
                                day_key = 'Tu'
                                i += 1
                            else:
                                day_key = 'Th'
                                
                        if day_key in schedule:
                            schedule[day_key].append({
                                'course': key, 
                                'start': start, 
                                'end': end
                            })
                        i += 1
        except Exception as e:
            print(f"Critical error fetching {key}: {e}")
            continue
            
    return schedule 


def parse_time(time_str):
    try:
        t = time_str.lower().strip()
        if not t or "tba" in t: 
            return None
            
        is_pm = 'pm' in t
        t = t.replace('am', '').replace('pm', '')
        
        # Split without using the word "map" to avoid colliding with your dictionary
        time_parts = t.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        
        if is_pm and hour != 12:
            hour += 12
        if not is_pm and hour == 12:
            hour = 0
            
        return hour + (minute / 60.0)
    except Exception as e:
        print(f"Time parsing error: {e}")
        return None

def draw_schedule(user_id):
    schedule_list = sch(user_id)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    days = ["M", "Tu", "W", "Th", "F"]
    day_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    colors = ['#E21833', '#FFD520', '#4285F4', '#34A853', '#9C27B0', '#FF6D00']
    course_colors = {}
    color_idx = 0

    min_hour = 8   
    max_hour = 17  

    for day_idx, day in enumerate(days):
        for cls in schedule_list[day]:
            start_float = parse_time(cls['start'])
            end_float = parse_time(cls['end'])
            
            if start_float is None or end_float is None:
                continue
                
            min_hour = min(min_hour, int(start_float))
            max_hour = max(max_hour, int(end_float) + 1)
            
            duration = end_float - start_float
            course = cls['course']
            
            if course not in course_colors:
                course_colors[course] = colors[color_idx % len(colors)]
                color_idx += 1
                
            bg_color = course_colors[course]
            text_color = 'black' if bg_color == '#FFD520' else 'white'
                
            ax.bar(day_idx, duration, bottom=start_float, width=0.85, 
                   color=bg_color, edgecolor='#333333', linewidth=1, align='center', alpha=0.95)
            
            ax.text(day_idx, start_float + (duration / 2), 
                    f"{course}\n{cls['start']} - {cls['end']}", 
                    ha='center', va='center', color=text_color, 
                    fontsize=10, fontweight='bold')

    ax.set_xlim(-0.5, 4.5)
    ax.set_xticks(range(5))
    ax.set_xticklabels(day_labels, fontsize=12, fontweight='bold')
    
    ax.set_ylim(max_hour + 0.5, min_hour - 0.5) 
    ax.set_yticks(range(min_hour, max_hour + 1))
    
    def format_hour(h):
        if h == 0 or h == 24: return "12:00 AM"
        elif h < 12: return f"{h}:00 AM"
        elif h == 12: return "12:00 PM"
        else: return f"{h-12}:00 PM"
        
    ax.set_yticklabels([format_hour(h) for h in range(min_hour, max_hour + 1)])
    
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    ax.set_axisbelow(True)
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    
    ax.set_title("Weekly Schedule", fontsize=16, fontweight='bold', pad=20)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close(fig)
    return buf
def draw_comparison(user1_id, user2_id, name1, name2):
    sched1 = sch(user1_id)
    sched2 = sch(user2_id)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    days = ["M", "Tu", "W", "Th", "F"]
    day_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    min_hour = 8   
    max_hour = 17  

    # Helper function to draw a schedule with a specific offset and color
    def plot_sched(schedule, offset, bg_color, text_color):
        nonlocal min_hour, max_hour
        for day_idx, day in enumerate(days):
            for cls in schedule[day]:
                start_float = parse_time(cls['start'])
                end_float = parse_time(cls['end'])
                
                if start_float is None or end_float is None:
                    continue
                    
                min_hour = min(min_hour, int(start_float))
                max_hour = max(max_hour, int(end_float) + 1)
                
                duration = end_float - start_float
                course = cls['course']
                
                # Shift the block left or right based on the offset
                x_pos = day_idx + offset
                
                # Make the width 0.42 so two blocks fit perfectly side-by-side in a 1.0 width column
                ax.bar(x_pos, duration, bottom=start_float, width=0.42, 
                       color=bg_color, edgecolor='#333333', linewidth=1, align='center', alpha=0.95)
                
                ax.text(x_pos, start_float + (duration / 2), 
                        f"{course}", 
                        ha='center', va='center', color=text_color, 
                        fontsize=9, fontweight='bold')

    # Draw User 1 shifted to the left (-0.22)
    plot_sched(sched1, -0.22, '#E21833', 'white') # Red
    # Draw User 2 shifted to the right (+0.22)
    plot_sched(sched2, 0.22, '#FFD520', 'black')  # Gold

    # Format the graph
    ax.set_xlim(-0.5, 4.5)
    ax.set_xticks(range(5))
    ax.set_xticklabels(day_labels, fontsize=12, fontweight='bold')
    
    ax.set_ylim(max_hour + 0.5, min_hour - 0.5) 
    ax.set_yticks(range(min_hour, max_hour + 1))
    
    def format_hour(h):
        if h == 0 or h == 24: return "12:00 AM"
        elif h < 12: return f"{h}:00 AM"
        elif h == 12: return "12:00 PM"
        else: return f"{h-12}:00 PM"
        
    ax.set_yticklabels([format_hour(h) for h in range(min_hour, max_hour + 1)])
    
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    ax.set_axisbelow(True)
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
        
    # Create a legend so you know who is who
    import matplotlib.patches as mpatches
    patch1 = mpatches.Patch(color='#E21833', label=name1)
    patch2 = mpatches.Patch(color='#FFD520', label=name2)
    ax.legend(handles=[patch1, patch2], loc='upper center', bbox_to_anchor=(0.5, 1.05), ncol=2, frameon=False, fontsize=12)
    
    ax.set_title("Schedule Comparison", fontsize=16, fontweight='bold', pad=40)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close(fig)
    return buf

@bot.hybrid_command(name='schedule')
async def schedule_command(ctx):
    await ctx.defer() 
    
    print(f"Drawing schedule for {ctx.author.name}")
    user_id_string = str(ctx.author.id)
    buf = await asyncio.to_thread(draw_schedule, user_id_string)
    file = discord.File(fp=buf, filename='schedule.png')
    
    await ctx.send("Here is your weekly schedule:", file=file)
@bot.hybrid_command(name='compare_visual')
async def compare_visual_command(ctx, target: discord.Member):
    await ctx.defer() 
    
    user1_id = str(ctx.author.id)
    user2_id = str(target.id)
    
    name1 = ctx.author.display_name
    name2 = target.display_name
    
    print(f"Drawing comparison for {name1} and {name2}")
    
    # Pass both IDs and names to the background thread
    buf = await asyncio.to_thread(draw_comparison, user1_id, user2_id, name1, name2)
    file = discord.File(fp=buf, filename='comparison.png')
    
    await ctx.send(f"Here is the side-by-side comparison for **{name1}** and **{name2}**:", file=file)
bot.run(os.getenv("DISCORD_TOKEN"))
