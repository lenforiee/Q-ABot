import os
import json
import random
import uuid
import asyncio
import discord
from difflib import SequenceMatcher
from discord.ext import commands

def _save_new_file(file_name: str, new_data: dict):
    with open(file_name, "w+") as stream:
        json.dump(new_data, stream, indent=3)
    print(f"Saved new data to {file_name}")

config = json.load(open("config.json"))
if os.path.exists("questions.json"):
    questions = json.load(open("questions.json"))
else:
    questions = {}
    _save_new_file("questions.json", questions)
hosts = config['hosts']
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

types = {
    'y/n': "Yes or No",
    "open": "Open",
    "choice": "Choice"
}

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.command(name="host")
async def host(ctx):
    if ctx.author.id != config['bot_owner']:
        return await ctx.send("You may not use this command!")

    args = ctx.message.content.split(" ")[1:]

    if not args:
        return await ctx.send("Invalid syntax! Example: !host <add/delete> <id>!")

    if args[0] == "add":
        if args[1].isdigit():
            hosts.append(int(args[1]))
            config['hosts'] = hosts
            _save_new_file("config.json", config)
            return await ctx.send(f"Added **{args[1]}** user id to hosts!")
    elif args[0] == "delete":
        if args[1].isdigit():
            hosts.remove(int(args[1]))
            config['hosts'] = hosts
            _save_new_file("config.json", config)
            return await ctx.send(f"Removed **{args[1]}** user id from hosts!")
    return await ctx.send("Invalid input!")

@bot.command(name="ask")
async def ask(ctx):
    def check(m):
        return m.author == ctx.message.author and m.channel.me.id == ctx.bot.user.id

    if not config['applications'] and ctx.author.id not in hosts:
        return await ctx.send("Questions are currently closed!")
    
    args = ctx.message.content.split(" ")[1:]
    question = {}
    abcs = {}
    await ctx.message.delete()

    if not args:
        return await ctx.author.send("Invalid syntax! !ask <type, `y/n`/`open`/`choice`>")

    if args[0] not in ("y/n", "open", "choice"):
        return await ctx.author.send("Invalid question type! available <`y/n`/`open`/`choice`>")
    
    question['type'] = types[args[0]]
    question['author'] = ctx.author.id
    await ctx.author.send(
        "Tell me person question is forwarded to!\n"
        "Note: You can use user id which is way better!\n"
        "PS: If you want to cancel your question type /cancel any time ;)\n"
        "Example: lenforiee or 291927822635761665"
    )
    while True:
        try:
            first = await ctx.bot.wait_for('message', check = check, timeout = 60)
        except asyncio.TimeoutError:
            return await ctx.author.send('Your 60 second is gone, and question was canceled!')
        if first.content == "/cancel":
            return await ctx.author.send("Question was canceled!")
        content = first.content
        question['to'] = content
        break
    await ctx.author.send(
        "Tell me whats the question!\n"
        "Example: Whats your fav colour?"
    )
    while True:
        try:
            second = await ctx.bot.wait_for('message', check = check, timeout = 60)
        except asyncio.TimeoutError:
            return await ctx.author.send('Your 60 second is gone, and question was canceled!')

        if second.content == "/cancel":
            return await ctx.author.send("Question was canceled!")
        content = second.content
        question['question'] = content
        break
    if args[0] == "choice":
        await ctx.author.send(
            "Please type the A.B.C.D answers\n"
            "Example: A. Red (can be mulitple)\n"
            "To save your answers type /finish"
        )
        while True:
            try:
                third = await ctx.bot.wait_for('message', check = check, timeout = 60)
            except asyncio.TimeoutError:
                return await ctx.author.send('Your 60 second is gone, and question was canceled!')

            if second.content == "/cancel":
                return await ctx.author.send("Question was canceled!")
            if third.content == "/finish":
                break
            if third.content.find(". ") == -1:
                await ctx.author.send("Wrong syntax! Example: A. Red")
                continue

            if third.content.find("\n") != -1:
                for i in third.content.split("\n"):
                    if i.find(". ") == -1:
                        continue
                    prefix, answer = i.split(". ")
                    abcs[prefix] = answer
            else:
                prefix, answer = third.content.split(". ")
                abcs[prefix] = answer
            
            if third:
                await ctx.author.send("Added answer!")
        question['abcs'] = abcs
    
    identif = str(uuid.uuid4())[8:]
    questions[identif] = question
    _save_new_file("questions.json", questions)
    return await ctx.author.send(
        f"Your question has been submitted with identifier **{identif}**\n"
        f"your question: **{question['question']}** forwarded to **{'id: ' + str(question['to']) if question['to'].isdigit() else question['to']}**\n"
        f"if you wish to delete your question type !delete <identifier>"
    )

@bot.command(name="delete")
async def delete(ctx):
    await ctx.message.delete()
    args = ctx.message.content.split(" ")[1:]

    if not args:
        return await ctx.author.send("Invalid syntax! !delete <identifier>")
    
    if args[0] in questions:
        if questions[args[0]]['author'] == ctx.author.id:
            del questions[args[0]]
            _save_new_file("questions.json", questions)
            return await ctx.author.send("Deleted the question!")

@bot.command(name="read")
async def read(ctx):
    args = ctx.message.content.split(" ")[1:]

    if not ctx.author.id in hosts:
        return await ctx.author.send("You may not use this command!")

    if not args:
        return await ctx.author.send("Invalid syntax! !read <identifier>")
    
    if args[0] in questions:
        quest = questions[args[0]]
        if quest['to'].isdigit():
            mention = f"<@{quest['to']}>"
        else:
            for member in ctx.message.channel.guild.members:
                if 0.7 <= SequenceMatcher(None, quest['to'], member.name).ratio():
                    mention = f"<@{member.id}>"
                    break
            else:
                mention = quest['to'] # No mention..
        
        answers = []

        if quest['type'] == "Choice":
            answers = [f"**{k}.** {v}" for k, v in quest['abcs'].items()]
        elif quest['type'] == "Yes or No":
            answers = ["**A.** Yes", "**B.** No"]

        answer = 'Answers:\n' + '\n'.join(answers) if answers else ''
        return await ctx.send(
            f"{quest['type']} question for {mention}\n\n"
            f"Question: **{quest['question']}**\n"
            f"{answer}"
        )
    return await ctx.send("Question doesnt exist!")

@bot.command(name="getrandom")
async def getrandom(ctx):

    if not ctx.author.id in hosts:
        return await ctx.author.send("You may not use this command!")

    if not questions:
        return await ctx.author.send("There is no questions at the moment!")

    quest = questions[random.choice(list(questions.keys()))]

    if quest['to'].isdigit():
        mention = f"<@{quest['to']}>"
    else:
        for member in ctx.message.channel.guild.members:
            if 0.7 <= SequenceMatcher(None, quest['to'], member.name).ratio():
                mention = f"<@{member.id}>"
                break
        else:
            mention = quest['to'] # No mention..
    
    answers = []

    if quest['type'] == "Choice":
        answers = [f"**{k}.** {v}" for k, v in quest['abcs'].items()]
    elif quest['type'] == "Yes or No":
        answers = ["**A.** Yes", "**B.** No"]

    answer = 'Answers:\n' + '\n'.join(answers) if answers else ''
    return await ctx.send(
        f"{quest['type']} question for {mention}\n\n"
        f"Question: **{quest['question']}**\n"
        f"{answer}"
    )

@bot.command(name="questions")
async def question(ctx):

    if ctx.author.id != config['bot_owner']:
        return await ctx.send("You may not use this command!")

    args = ctx.message.content.split(" ")[1:]

    if not args:
        return await ctx.send("Invalid syntax! Example: !questions <on/off>!")

    if args[0] == "on":
        config['applications'] = True
        _save_new_file("config.json", config)
        return await ctx.send("Questions has been enabled!")
    elif args[0] == "off":
        config['applications'] = False
        _save_new_file("config.json", config)
        return await ctx.send("Questions has been disabled!")
    else:
        return await ctx.send("Invalid args!")


bot.run(config['token'])