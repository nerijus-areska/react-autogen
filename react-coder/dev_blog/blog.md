# Hostinger Homework analysis
## Initial impression
So apparently what they want is fairly open-ended. I am supposed to build a REST API which modifies the code of a project.
Not sure how to read this though: _Any other method you consider relevant_ 
They also seem to suggest they only need the backend, but this is very limiting. How am I supposed to test this without a basic client? I will write something cmdline friendly to juggle sessions at least.
I also want to start attacking this with Qwen3 Coder 30b A3b, 4bit quant. Once it fails somewhere, I will switch to Qwen3 Next Coder 80b, 8bit quant ( if KV cache does not kill me )
I should save some time in the end to make sure some OpenAI model is good enough for the demo.

## Architecture
Ok, so the plan is to create server ( and client ) in the same repo root directory.
Since we likely never want to modify files directly, and the projects are tiny, I can treat each interaction ( multi-step will come in handy here ) as a session, and copy the whole project to a temp directory ( symlink node_modules, if I want to see it work, no need to copy that ). Then I want to have some idea of a workflow ( with Strategy pattern ). I want to have multiple of them at once, so I could switch from the client and demonstrate why one is better than another ( token usage, speed, correctness, capabilities).
So the workflow would ideally do any modifications it needs
Oh, I just realized: having multiple workflows at once is actually nice not only for demo purposes. Ideally I would like to judge user's requests and route them to a specific workflow based on their complexity. This should save both tokens and time.

## Some more thoughts after looking at the sample REACT projects
- Did they want to expose plugins??? LOL, this is actual production Horizons project it seems. I should not care I guess and limit myself to src directory
- tools/generate-lms.js is also likely unintentionally leaked
- Ok, I went through the projects - they are extremely simplistic.. And likely any complex workflow I will make will fail because of that simple architecture. I wonder if I need to create a fourth project, just to have a more serious directory structure? ( I don't need to do this now though, but it should be an option ) .. or I can refactor one of them
- everything's client side too, it's fine, but I wonder if it does not limit me too much

# DEV Blog
Cloning some basic Fast API - I think I won't need any database for this. Infrastructure is trivial - just allow worfklow to work within a context of one folder (src). After the worfklow is done  - do a git diff and return that to the client.
I added the client too - it's super simple (it just takes care of session_id), /init and /stop are nice, since I can make modifications over multiple steps. Also I can display git diffs with nice colors.

Oh, another nice thing with the client - I added --run, so I can actually open browser from the client and  have the app running and see the changes LIVE, while react-coder workflow is working!

## First workflow

Ok, I got the first workflow somewhat running. So it's super basic (but I think Aider might be doing something similar in non-architect mode). The flow is:
- Compile the file tree of the project ( with some metadata, function names, etc )
- give the user prompt plus the file tree to LLM, ask for the list of files he needs
- read the files, concatenate them into a single message, repeat the user's prompt again, now we're asking for a JSON with files and their contents
- (skipping the chat history between orchestrator and LLM fully. Every message should provide enough context, previous steps are really irrelevant in this workflow)
- parse the response, replace the files in FS with files from the response, return

First task is to change the todo-app button color
I tried Qwen2.5 7b coder  for fun. Arghh, I really remember it working with Aider..? Maybe not, two issues immediately:
- it consistently asks for button.jsx - but it messes up the path :(
	1. we actually don't need button.jsx for this task, so I will just not append the file if I can't find it :)
	2. this is a huge red flag though
- It messes up the response format ( it keeps wrapping file content in single quotes ( actually backticks), when asked to use double quotes...)
	- I can maybe postprocess that, but it's stupid at the moment

Switching to Qwen3 30b Coder. Ok, great - first try is amazing, on to documenting test cases

### Test Cases
#### In my Todo App - change the button color of "Add Todo" from black to blue
**Supposedly trivial**

First try: [9926_chatlog](logs/9926_chatlog.txt) 
Main model: _qwen3-coder-30b-a3b-instruct-mlx_
Initializing
![](images/Pasted%20image%2020260213145529.png)
Prompting, and In few seconds: 
![](images/Pasted%20image%2020260213150158.png)

#### In the TODO App Add a 'Clear Completed' button below all tasks. It should delete all completed tasks

**Functional task** 

First try: [ba81_chatlog](logs/ba81_chatlog.txt)
Model: _qwen3-coder-30b-a3b-instruct-mlx_
(Button works too)

![](images/Pasted%20image%2020260213171723.png)

#### Add a search box bellow the stats panel to filter Todo tasks by name

**Complex task**

First try: [837b_chatlog](logs/837b_chatlog.txt)
Model: _qwen3-coder-30b-a3b-instruct-mlx_

So as I already have seen with this model before - and this is obvious from the chat log - once we expand a context a bit with 30b qwen3, it tends to go off the rails completely.

Anyway - I wanna try some of the OpenAI models, since any demo I make will probably use them anyway.

Second try: [8e79_chatlog](logs/8e79_chatlog.txt)
Model: *gpt-5-mini*

![](images/Pasted%20image%2020260214104526.png)

gpt-5-mini is miles ahead of qwen 30b. Well it's _almost_ amazing, functionality works great. Screenshot kinda shows that the search text is all white text - and is only visible when selected :)

After further research **I have Hit a Conundrum**......
The *1-todo-app* looks flawed, it has text-white on body in the index.css, it almost seems like they did it for HomePage.tsx, but then used inline-styles for TodoApp.tsx.
Global styles should be neutral defaults, or even better - there should be a theme provider present, since we likely want to switch between light/dark

I have two options now:
- assume this is part of the homework, and I need to deal with refactoring of badly written apps
- Since this tool itself is potentially writing the app - it should never generate in the first place

I wanna go with option 2, since that's how I would write a new project. Actually, let's go to the next app.

One more thing - I want to improve client a bit, since now I am using gpt-5 (and they give me some free tokens each day), I want to display as much as I can in the client. So this is nice now

![](images/Pasted%20image%2020260214114108.png)

#### Candy shop: I moved my shop, current address now is Gedimino pr. 11


First try: [2d27_chatlog](logs/2d27_chatlog.txt)
Model: *gpt-5-mini*

![](images/Pasted%20image%2020260214171040.png)

I feel the second project is even easier than the first, and it's getting repetitive, moving to the third right away

#### Add a Button below the bar code to directly copy the QR Code image into the clipboard

First try: [c91f_chatlog](logs/c91f_chatlog.txt)
Model: *gpt-5-mini*

![](images/Pasted%20image%2020260214172515.png)

#### In the Todo app - add undo/redo functionality with complete action history

First try: [cd7c_chatlog](logs/cd7c_chatlog.txt)
Model: *gpt-5-mini*

![](images/Pasted%20image%2020260214180642.png)

I did not expect this to succeed for some reason..., I need something even more complex

#### Add projects functionality. Each Todo may belong to a project. We also need to be able to manage projects

First try: [eddf_chatlog](logs/eddf_chatlog.txt)
Model: *gpt-5-mini*

![](images/Pasted%20image%2020260214181405.png)

I am growing desperate - somehow this was flawless... And it Changed THREE files at once, 7k output tokens of course - but still.. Really? This needs more kick

#### THE Hard problem

```
Todos should have projects and due dates. We need three more pages (use React Router).
* One to manage projects
* One for Kanban view with drag and drop and 3 columns: New, Working, Done
* One for Calendar view - which would show each TODO for their respective due date in the correct day slot
Do not use any external libraries or packages.
```

![](images/Pasted%20image%2020260214184606.png)
![](images/Pasted%20image%2020260214184624.png)

![](images/Pasted%20image%2020260214184633.png)

This is crazy really, 12k tokens..., but this is somehow working 100%

**THE INTERVENTION TIME**
```
I cannot continue trying to crash the first workflow. I mean I could just create a way more complicated project ( maybe with backend ). But I really have no time for this. 
But I DO NOT need the more complex workflow for any of these problems..

I guess I do it anyway.. just to prove it works maybe?
```
## Second workflow

### Router first

I reason now - I might as well add the router, since we will have multiple workflows.. Well, since I will only have two for now - we can do this:

```
You are a router for a code-editing system. Given the user's instruction, choose exactly one workflow.

User instruction: "Change the color of the Add Todo button to Blue"

Available workflows:
- simple_modification: Basic file identification and single-pass modification. Best for simple styling, text changes, or single-component edits. (complexity: simple)
- explorative_modification: Advanced workflow using tool-based exploration. LLM explores codebase with grep/search tools and makes targeted edits. Best for complex multi-file changes. (complexity: advanced)

Respond with a JSON object only, no other text:
{"workflow": "<name>", "reason": "<one short sentence>"}

Use exactly one of these workflow names: simple_modification, explorative_modification.
```

### Test cases

We can actually try two prompts now to prove router works!
- Change the color of the Add Todo button to Blue
- Now add a Projects page ( use React Router ), we want to manage projects in there, also when adding Todo Items we should be able to select a project. Projects should also be visible as tags next to each Todo

First try: [839e_chatlog](logs/839e_chatlog.txt)
Hmm, so I got this error:
`ERROR:app.workflows.explorative_modification.workflow:Failed to parse LLM response: Invalid JSON in LLM response: Extra data: line 2 column 1 (char 277)`

Which is not surprising since chatlog ends with this, which yep.. NOT a JSON:
```
{"thought":"Listing files in src and components/pages to understand structure","tool_calls":[{"tool":"list_files","parameters":{"directory":"src"}},{"tool":"list_files","parameters":{"directory":"src/components"}},{"tool":"list_files","parameters":{"directory":"src/pages"}}]}
(Note: I'm waiting for tool outputs.)
```

And we have this in our prompt:!!!, It's so weird that gpt5-mini have not failed with the JSON EVER up till this point..
`....Respond with a JSON object only, no other text:....`

Instead I will try to detect JSON, if it takes > 20% of the response - I guess we just use that

#### Minor intervention
There's a bunch of bugs, and I need some improvements, so adding
- measuring time taken in the client, so I can compare workflows
- Also measuring $ cost for each workflow ( we already count input/output tokens anyway)
- Most of the bugs in the tool caller are from path issues ( since we do everything from within "src", but LLM often includes "src" in the tool calls). So adding few normalization helpers into tool caller workflow ( TODO: I should probably add normalization to base workflow )
- saving workflow chatlogs separately - these are easier to read than raw chat logs ( still keeping those for debug purposes for a while at least, TODO: remove `_chatlog` format fully)

Sixth or seventh try (new format for chat logs): [66aa_workflow](logs/66aa_workflow.txt)
![](images/Pasted%20image%2020260215130524.png)

Worfklow summary (from server logs):
```
=== Workflow summary ===
Total tool calls: 3  |  Total tool time: 0.01s

Tool usage (count):
  apply_edit: 1
  grep_code: 1
  read_file_lines: 1

Tool duration (visual, each bar = one call):
  apply_edit:
    [█░░░░░░░░░░░░░░░░░░░░░░░] 0.00s
  grep_code:
    [████████████████████████] 0.01s
  read_file_lines:
    [█░░░░░░░░░░░░░░░░░░░░░░░] 0.00s
```

Actually, since I have a ton more data in the client - let's rerun it with simple_modification forced ( no router ):
![](images/Pasted%20image%2020260215131941.png)

The Tool caller wins this easily! Of course there's way more input tokens (5k vs 1.5k, since we need to explain all the tools to LLM). 
BUT, there's less output tokens (0.8k vs 1.7k, because LLM does not need to output the whole file), which then makes it cheaper to run!! _$0.0028 vs $0.0039_
Also - and this is even more impressive, we have : _10.7s vs 16.5s_ <----- BECAUSE tool caller generates LESS output tokens. So the UX is WAY better.
And this is WHILE the main file in question, TodoForm.jsx is **43 LINES LONG**

## Exploration and synthesis
Let's add all the previous user questions into both workflows (so we can ask "Actually, I changed my mind, change it to green", LLM should be aware what "it" is)
This should enable semi-true multi-turn ( since we're not adding responses )
Also - let's use multi-turn flow to develop a bigger app and record both workflows in detail


### Explorative Multi-turn
`change the Add Todo button color from black to green`

![](images/Pasted%20image%2020260215160745.png)

`Now add a red button to clear all the completed todo tasks in the bottom`

![](images/Pasted%20image%2020260215160957.png)

`I hate the add todo button color - change it back`
![](images/Pasted%20image%2020260215161105.png)
Snippet from workflow (To prove "Change it back" knew what to change it back to):
```
================================================================================

[USER]
You are an expert code modification agent working on a React codebase.


PREVIOUS USER COMMANDS (for context; current task is below):
- change the Add Todo button color from black to green
- Now add a red button to clear all the completed todo tasks in the bottom

TASK: I hate the add todo button color - change it back
```

Workflow log: [e240_workflow](logs/e240_workflow.txt)
Total time taken: 13.3+32.8+15.9=**62s**
Total input tokens: *38,676*
Total output tokens: *5,269*
Total estimated cost: *$0.0202*

### Simple multi-turn
`change the Add Todo button color from black to green`
![](images/Pasted%20image%2020260215161918.png)
`Now add a red button to clear all the completed todo tasks in the bottom`
![](images/Pasted%20image%2020260215161954.png)
`I hate the add todo button color - change it back`
![](images/Pasted%20image%2020260215162104.png)

Chatlog: [9d90_chatlog](logs/9d90_chatlog.txt)
Total time taken: 10.6+34.2+12.6=**57.4s**
Total input tokens: *4,271*
Total output tokens: *4,810*
Total estimated cost: *$0.0107*
# Conclusions
The last multi-turn chat turned out - the simple modification route while writing whole files performed twice cheaper compared to tool user.
It's pretty surprising that tool user consumed a tiny bit more output tokens.. but why??

- Well, the most of the tokens were generating new functionality, so that's equal for both of them
- for very simple cases, like changing button color, tool user adds all the tool calls anyway - and these sum up to more, than simple modificator just outputting the full file.. ( since the file is small! )
- I think the tool user can be tuned to outperform the full file modification with more direct instructions


# Afterthoughts
- I have been using gpt5-mini throughout this project, BUT - it's crucial to note, the knowledge cutoff is 2024-09, compared to 2025-09 for gpt5.2 (output tokens: $2 vs $14)
	- This is very important considering we're using Tailwind CSS ( v4 released 2025-01, in the middle between gpt5-mini and gpt5.2)
	- The projects use v3, so we're fine, but moving forward - if we care about the token cost - we should NOT upgrade to v4
- There's a gazillion of edge cases - conflicting/wrong/vague user prompts possible. I tried writing these prompts as a non-techie, but I am suffering from a HUGE knowledge curse. This is a _weak point_ of this project (it may not be shippable in such architecture at all)
- I completely ignored security. Tool caller workflow is executing shell commands freely. The hack attempts are quite hard to execute though. And in this case they would be done by paying users, who have credit card information on the website builder.. I really doubt they are doing any attacks whatsoever, so maybe that's not a huge issue?
- I also ignored linting and retries. Not really needed while researching the project, but critical in prod (and I had few cases of failures)
- The App given to me was not a correct React app. I think we can get way better results (at least with simple_modification workflow), if we force a proper directory structure from Prompt 1, smthing like this:
  ![](images/Pasted%20image%2020260215133656.png)
Having features as separate microcosms, allows for having a clear separation of concerns, and MUCH smaller files, which then should save on output tokens for simple_modification workflow.
Also tool caller (explorative_modification) might benefit from easier identifying what needs to be changed ( and saving on input tokens too )