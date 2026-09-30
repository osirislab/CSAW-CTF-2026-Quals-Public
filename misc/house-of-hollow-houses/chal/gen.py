#!/usr/bin/env python3
"""Generator for the lhohq-style CTF maze: 100 pages, 6-step golden path, 94 distractor loop."""
import os, random, base64, codecs, textwrap

random.seed(1729)
ROOT = os.path.dirname(os.path.abspath(__file__))

# ────────────────────────── ROOMS ──────────────────────────

GOLDEN = ['atrium','ossuary','mirror','wellspring','sanctum']  # path 1..5; index is 0

DISTRACTORS = [
  'corridor','vestibule','chapel','cistern','attic','catacomb',
  'garden','scullery','library','hollow','narthex','transept',
  'oratory','crypt','parlour','pantry','gable','eaves','fascia',
  'threshold','stair','landing','foyer','atelier','observatory',
  'balcony','conservatory','reliquary','antechamber','cellar',
  'dovecote','morgue','sacristy','undercroft','refectory',
  'scriptorium','columbarium','lazaret','mortuary','ambulatory',
  'cloister','rectory','presbytery','baptistery','chantry',
  'chancel','apse','nave','aisle','gallery','dormitory',
  'hall','kitchen','dining','study','parlor','sitting','smoking',
  'billiard','music','drawing','ballroom','lounge','dressing',
  'bathroom','larder','buttery','brewhouse','dairy','henhouse',
  'smithy','mill','granary','silo','barn','stable','kennel',
  'mews','lodge','gatehouse','guardroom','watchtower','belfry',
  'steeple','tower','turret','dungeon','oubliette','cell',
  'vault','cache','alcove','niche','nook',
]
assert len(DISTRACTORS) == 94, f"distractor count = {len(DISTRACTORS)}"

# ────────────────────────── PALETTES ──────────────────────────
# haphazard low-contrast pairings. each page picks one at random.

PALETTES = [
  {"bg":"#2a0d18","fg":"#d4c87a","dim":"#5a3a2a","accent":"#7a3a28","link":"#a8884a","linkh":"#f0e0a0"},
  {"bg":"#0d2a18","fg":"#e0a878","dim":"#2a4a3a","accent":"#3a7a48","link":"#7ab888","linkh":"#a8e8c0"},
  {"bg":"#1a1a3a","fg":"#a8c4e0","dim":"#3a3a5a","accent":"#4a3a8a","link":"#7898c8","linkh":"#c0d8f0"},
  {"bg":"#3a2a0d","fg":"#d8d8d8","dim":"#5a4a2a","accent":"#8a6a3a","link":"#c8a878","linkh":"#f0e0c0"},
  {"bg":"#0a0a0a","fg":"#7a3a28","dim":"#2a1a1a","accent":"#3a0a08","link":"#a85838","linkh":"#e08858"},
  {"bg":"#1a2a2a","fg":"#d8c8b0","dim":"#3a4a4a","accent":"#5a7a7a","link":"#a8a888","linkh":"#e8e8c0"},
  {"bg":"#2a1a0d","fg":"#a8c878","dim":"#4a3a2a","accent":"#5a3a1a","link":"#88a858","linkh":"#c8e8a0"},
  {"bg":"#0d0d2a","fg":"#d8a878","dim":"#2a2a4a","accent":"#3a3a7a","link":"#a87858","linkh":"#e8c898"},
  {"bg":"#2a0d2a","fg":"#a8d8a8","dim":"#4a2a4a","accent":"#5a3a5a","link":"#88b888","linkh":"#c8f0c8"},
  {"bg":"#1a2a0d","fg":"#d8c878","dim":"#3a4a2a","accent":"#3a5a1a","link":"#b8a858","linkh":"#f0e0a0"},
  {"bg":"#0d2a2a","fg":"#d8a8c8","dim":"#2a4a4a","accent":"#3a5a5a","link":"#b888a8","linkh":"#f0c8e0"},
  {"bg":"#3a1a1a","fg":"#c8b878","dim":"#5a3a2a","accent":"#7a4a3a","link":"#a89858","linkh":"#e8d898"},
  {"bg":"#1a0d2a","fg":"#a8a8d8","dim":"#3a2a4a","accent":"#3a2a5a","link":"#8888b8","linkh":"#c8c8f0"},
  {"bg":"#0d1a0d","fg":"#7a8a3a","dim":"#1a2a1a","accent":"#2a3a2a","link":"#5a6a2a","linkh":"#a8b858"},
  {"bg":"#2a2a0d","fg":"#a8d8d8","dim":"#4a4a2a","accent":"#5a5a3a","link":"#88b8b8","linkh":"#c8f0f0"},
  {"bg":"#1a0d0d","fg":"#8a7a6a","dim":"#2a1a1a","accent":"#3a2a2a","link":"#6a5a4a","linkh":"#b8a898"},
  {"bg":"#0d0d1a","fg":"#5a7a8a","dim":"#1a1a2a","accent":"#1a1a3a","link":"#4a6a7a","linkh":"#88a8b8"},
  {"bg":"#2a1a2a","fg":"#d8d8a8","dim":"#3a2a3a","accent":"#4a3a4a","link":"#b8b878","linkh":"#f0f0c0"},
  {"bg":"#1a2a1a","fg":"#c8a8a8","dim":"#2a3a2a","accent":"#3a5a3a","link":"#a88888","linkh":"#e8c8c8"},
  {"bg":"#0d1a1a","fg":"#a8c8a8","dim":"#1a2a2a","accent":"#1a3a3a","link":"#88a888","linkh":"#c8e8c8"},
  {"bg":"#1a1a1a","fg":"#d0a8d0","dim":"#2a2a2a","accent":"#3a3a3a","link":"#a888a8","linkh":"#e0c0e0"},
  {"bg":"#0a1a0a","fg":"#cab87a","dim":"#1a2a1a","accent":"#2a4a2a","link":"#a8985a","linkh":"#e8d89a"},
  {"bg":"#180a18","fg":"#d8c0a0","dim":"#2a1a2a","accent":"#5a3a5a","link":"#b89878","linkh":"#f0d0a8"},
  {"bg":"#0d181a","fg":"#a8b8c0","dim":"#1a282a","accent":"#3a484a","link":"#7898a0","linkh":"#c0d0d8"},
]

# ────────────────────────── FONTS ──────────────────────────

FONTS = [
  '"EB Garamond", serif',
  '"IM Fell English", serif',
  '"Special Elite", monospace',
  '"UnifrakturCook", serif',
  '"Cormorant Garamond", serif',
  '"Cinzel", serif',
  '"Pirata One", serif',
  '"Old Standard TT", serif',
  '"Cardo", serif',
  '"Crimson Text", serif',
  '"MedievalSharp", serif',
  '"Cormorant Unicase", serif',
]

# ────────────────────────── ATMOSPHERE ──────────────────────────

GLYPHS = ['☉','☽','☿','♀','♁','♂','♃','♄','☥','☦','☧','☨','☪','✚','✝','✞','✟','✠','✡',
          '⚝','☘','♆','♇','☄','☼','⚰','⚱','⚖','⚗','⚘','⚙','⚛','⚜','✦','✧','✩','✪','✫',
          '✬','✭','✮','✯','✰','✱','✲','✳','✴','✵','✶','✷','✸','✹','✺','✻','✼','✽','✾',
          '✿','❀','❁','❂','❃','❄','❅','❆','⚸','⚹','⚺','⚻','⚼','⚷','☬','☫','☭','☮','☯',
          '☸','♰','♱','✠','⛧','⚸','☥','⚚','☤','⚕','♅','♆','♇','♈','♉','♊','♋','♌','♍']

SUBTITLES = [
  "a room that was not waiting for you",
  "the long stillness before the question",
  "kept apart from the rest, by arrangement",
  "named for a thing that has not survived its naming",
  "below the floor that is below the floor",
  "the chamber the caretaker prefers to forget",
  "a small persistence of architecture",
  "left as it was found, which was not, on the whole, found",
  "the room that has agreed not to be measured",
  "the third such room, by a count that has been disputed",
  "where the light arrives sideways and stays",
  "a hollow set aside for the kneeling of strangers",
  "older than the visitors. older than the visit.",
  "a quiet inventory of regrets",
  "between the wall and the next wall",
  "the room that prefers its visitors to be brief",
  "an architecture of small refusals",
  "the place where the wallpaper has begun to listen",
  "an interior of indifferent weather",
  "the chamber the house has on more than one occasion misplaced",
  "the only room with no name on the older plans",
  "a corner the floorplan has agreed to allow",
  "kept against the day of an inspection that does not arrive",
  "the antechamber of a chamber that is not in the house",
  "a small enclosure for purposes the house has not declared",
]

FOOTERS = [
  "the house thanks you for your visit. the house has, of course, already forgotten you.",
  "you are no longer here. you have not yet been here. the difference is the room.",
  "visitor record retained against the day of an audit which the house knows will not come.",
  "the caretaker is, as ever, elsewhere. the house regrets the inconvenience.",
  "what you brought with you, you may take with you. what you found here, you may not.",
  "the door behind you is now a wall. this is not new. this is the usual arrangement.",
  "your name has been added to the list. the list is, the house insists, very long.",
  "the lights have been dim, but for you they have not been off. the house extends this small courtesy.",
  "this page was not, on opening, the page it was a moment ago.",
  "if you have read this far, you have been read further.",
]

# ────────────────────────── PROSE TEMPLATES ──────────────────────────
# placeholders: {r1} {r2} {r3}. each pre-substituted with linked rooms.

TEMPLATES = [
  "The {r1} is full of {r2}. It was, on a clear day, mistakable for a {r3}, but the misapprehension has not, on the whole, survived contact with the wallpaper.",
  "Visitors who pass through the {r1} are expected to leave their hats at the door. The door is in the {r2}. The {r2} has, since 1947, kept the hats in a basket the colour of which no one has been able to agree on.",
  "There is a {r1} beneath the {r2}. There is, beneath the {r1}, another {r2}. The house has, on this subject, declined to be questioned further.",
  "The {r1} was decorated, in 1903, by a woman who is now in the {r2}. She has not, on any subsequent occasion, asked to be moved.",
  "Do not enter the {r1} without first consulting the {r2}. The {r2} will not answer, but it will, after a fashion, listen.",
  "The {r1} contains a chair. The chair contains an opinion. The opinion concerns the {r2}, and the {r2}, on hearing it, has elected to remain silent.",
  "If you find yourself in the {r1}, the {r2} is two doors to your left, and three doors to your right, and either way you are, by the time you arrive, in the {r3}.",
  "The {r1} keeps a list. The list is of every visitor who has ever asked, on entering, where the {r2} is. The list is bound; the list is long; the list is the {r1}, written down.",
  "Between the {r1} and the {r2} lies a passage no one will admit to having built. The passage is called the {r3}, although the {r3} is, on the whole, something else.",
  "The {r1} was, in an earlier century, the {r2}. The {r2} was, before that, the {r3}. The house considers these distinctions, on its better days, ornamental.",
  "Ask the {r1} for the time. The {r1} will tell you it is later than you think. It will not specify than what.",
  "The {r1} smells, faintly, of the {r2}. This is not, the house insists, intentional. It is, however, persistent, and the visitors have learned, in time, to find it reassuring.",
  "A figure has been seen in the {r1}. The figure does not speak. The figure does not move. The figure is described, in the visitors' journals, as resembling the {r2}, which is to say as resembling no one in particular.",
  "The {r1} is closed for the season. The season is not specified. The {r2} has, on inquiry, declined to clarify.",
  "Three visitors entered the {r1} on the same morning, in 1971. Only two of them, when the count was taken, could be accounted for. The third is, the house assures us, in the {r2}, and is well, and prefers not to be disturbed.",
  "The {r1} has acquired, over the years, a peculiar habit of being where the visitor is not. This is not a fault of the room. It is, on most days, the visitor's.",
  "Beneath the floorboards of the {r1} is a small bell. The bell is rung, on certain evenings, by no one. The {r2} has been blamed; the {r2} has, in its turn, denied any involvement.",
  "The wallpaper in the {r1} is, on inspection, a repeating pattern of the {r2}. On closer inspection it is the same {r2}, every time. On closer inspection still it is the visitor.",
  "The {r1} keeps the keys to the {r2}. The {r2} keeps the keys to the {r3}. The {r3} keeps no keys; the {r3} is, the house insists, beyond locking.",
  "It is not advisable to read aloud in the {r1}. The {r1} retains what it hears, and it has, over the years, learned to recite.",
  "The {r1} contains a window. The window is not, on most days, a window. It is, on most days, the {r2}, and the {r2} is, on most days, kept closed.",
  "Visitors who linger in the {r1} have, on rare occasions, been observed to slowly resemble it. The house considers this an honour. The visitors, when they can still speak, are divided.",
  "There is a {r1} on the floor. There is, properly speaking, a {r1} for every floor. The house has confirmed this; the house keeps records; the records are kept in the {r2}, which is, in turn, on a floor of its own.",
  "On the wall of the {r1} hangs a portrait of the {r2}. The portrait is unsigned. The {r2} does not, on any account, recognise the likeness.",
  "If you stand in the {r1} and whisper the name of the {r2}, the {r2} will, very faintly, whisper back. It will not, on any occasion, whisper your name.",
  "The {r1} was sealed in 1944. The {r1} was opened in 1944, by a different hand, on a different schedule, for reasons the {r2} has agreed not to record.",
  "What is kept in the {r1} is not, in any meaningful sense, kept. It is merely, on most days, present. The visitors have been asked not to inquire further.",
  "The {r1} is the only room in the house that has never been described in the visitors' journals. The visitors have, on entering, generally forgotten how to write.",
  "Two staircases descend from the {r1}. One arrives at the {r2}. The other arrives at the {r2}. The arrival is, in either case, the same; the descent is not.",
  "Do not stand at the centre of the {r1}. The centre of the {r1} is, by long arrangement, reserved for the {r2}, which is not, at the time of writing, in the building.",
  "A draft moves between the {r1} and the {r2}. The draft, on cold nights, carries the sound of a conversation that took place in the {r3}, in a year the house has been asked not to specify.",
  "Above the lintel of the {r1} is carved a word. The word is not in any of the languages the house has been taught. The {r2} has offered, on several occasions, to translate it. The offer has not, to date, been accepted.",
  "The {r1} was, at one point, twice its present size. The other half is in the {r2}, and is not, the house insists, available for inspection.",
  "There is a clock in the {r1}. The clock keeps perfect time. The time it keeps perfect is not, however, the time being kept anywhere else in the building.",
  "The {r1} is named for a person. The person is not, the house notes, anyone the visitor will recognise. The {r2} keeps the relevant correspondence, which the visitor is not, in any case, encouraged to read.",
  "Of all the rooms in the house, the {r1} is the one the house is least proud of. The house has been asked, on more than one occasion, to demolish it. The house has, on more than one occasion, declined.",
  "If you sit very still in the {r1}, you may hear the floor above shift, slightly, in your direction. The floor above is the {r2}, and is, at the time of writing, unoccupied.",
  "The {r1} has been described, by certain visitors, as oppressive. The {r2} has, in writing, disagreed. The matter is considered closed.",
  "The lock on the door of the {r1} is on the inside. The key is in the {r2}. Visitors are advised to plan accordingly.",
  "What the {r1} lacks in the {r2} it makes up for in the {r3}. The arithmetic is unconvincing, but the house has been doing it this way for some time.",
]

PARA_CLASSES = ['', '', '', '', 'tight', 'cormorant', 'type', 'fell', 'indent', 'tilt-l', 'smear', 'wide', 'tilt-r', '']
INLINE_DECORATIONS = ['', '', '', 'flicker', 'shake', 'breathe', 'smear', 'tilt-l', 'tilt-r', 'faint', '']

# ────────────────────────── HELPERS ──────────────────────────

def linked(slug, label=None, link_class=""):
  c = f' class="{link_class}"' if link_class else ""
  return f'<a href="/{slug}/"{c}>{label or slug}</a>'

def deco_span(text):
  cls = random.choice(INLINE_DECORATIONS)
  if not cls or len(text) < 4:
    return text
  parts = text.split(' ')
  # only wrap words that don't contain any html tag characters or entity edges
  candidates = [i for i, p in enumerate(parts)
                if p.strip() and all(c not in p for c in '<>"&=/')]
  if not candidates:
    return text
  i = random.choice(candidates)
  parts[i] = f'<span class="{cls}">{parts[i]}</span>'
  return ' '.join(parts)

def make_paragraph(pool):
  tmpl = random.choice(TEMPLATES)
  n_slots = sum(1 for k in ('{r1}','{r2}','{r3}') if k in tmpl)
  picks = random.sample(pool, k=min(n_slots, len(pool)))
  # ensure 3 always available
  while len(picks) < 3:
    picks.append(random.choice(pool))
  sub = {'r1':linked(picks[0]),'r2':linked(picks[1]),'r3':linked(picks[2])}
  text = tmpl.format(**sub)
  text = deco_span(text)
  cls = random.choice(PARA_CLASSES)
  if cls:
    return f'<p class="{cls}">{text}</p>'
  return f'<p>{text}</p>'

def make_huge_aside():
  words = random.choice([
    ('read', 'slowly'),
    ('walk', 'walk'),
    ('listen', 'don\'t'),
    ('turn', 'turn'),
    ('wait', 'wait'),
    ('look', 'away'),
    ('kneel', 'don\'t'),
    ('down', 'further'),
    ('up', 'up'),
    ('open', 'don\'t'),
  ])
  tilt = random.choice(['tilt-l','tilt-r','tilt-2','tilt-3'])
  return f'<p class="huge {tilt} smear">{words[0]} &nbsp; <span class="flicker">{words[1]}</span></p>'

def make_map_section(pool, n=40):
  picks = random.sample(pool, k=min(n, len(pool)))
  pieces = []
  for r in picks:
    label = r
    if random.random() < 0.18:
      # mutilate label cosmetically — different visible name, same href
      label = random.choice([
        f'<em>{r}</em>',
        f'<span class="tilt-l">{r}</span>',
        f'<span class="faint">{r}</span>',
        f'<span class="reflected">{r}</span>',
      ])
    pieces.append(f'the <a href="/{r}/">{label}</a>')
  text = ', '.join(pieces) + '.'
  return f'<h3>passages</h3><p class="cols tight tiny">{text}</p>'

def random_eye_svg(stroke):
  # vary shape slightly
  rx = random.randint(60, 100)
  ry = random.randint(14, 30)
  pupil = random.randint(8, 16)
  return f'''<svg class="eye" width="220" height="120" viewBox="0 0 220 120" xmlns="http://www.w3.org/2000/svg">
    <g fill="none" stroke="{stroke}" stroke-width="1">
      <path d="M5,60 Q110,5 215,60 Q110,115 5,60 Z"/>
      <ellipse cx="110" cy="60" rx="{rx}" ry="{ry}"/>
      <circle cx="110" cy="60" r="{pupil*2}"/>
      <circle cx="110" cy="60" r="{pupil}" fill="{stroke}" />
    </g></svg>'''

def page_style(palette, n_paras):
  """generate inline <style> with palette + random per-element font assignments"""
  body_font = random.choice(FONTS)
  h1_font = random.choice(FONTS)
  h2_font = random.choice(FONTS)
  h3_font = random.choice(FONTS)
  # assign a different font to every 2nd, 3rd, 5th, 7th paragraph
  rules = []
  for n in [2,3,4,5,6,7,8,9,11,13]:
    rules.append(f'main p:nth-child({n}n){{font-family:{random.choice(FONTS)};}}')
  # random spans get random fonts
  rules.append(f'.cormorant{{font-family:{random.choice(FONTS)};font-style:italic;}}')
  rules.append(f'.type{{font-family:{random.choice(FONTS)};}}')
  rules.append(f'.fell{{font-family:{random.choice(FONTS)};font-style:italic;}}')
  rules.append(f'.huge{{font-family:{random.choice(FONTS)};}}')
  rules.append(f'em{{font-family:{random.choice(FONTS)};font-style:italic;}}')
  rules.append(f'strong{{font-family:{random.choice(FONTS)};font-weight:400;}}')
  # haphazard inline link tinting per page
  link_alt1 = random.choice([palette['fg'], palette['link'], palette['accent'], palette['linkh'], palette['dim']])
  link_alt2 = random.choice([palette['fg'], palette['link'], palette['accent'], palette['linkh'], palette['dim']])
  rules.append(f'main p:nth-child(3n) a{{color:{link_alt1};}}')
  rules.append(f'main p:nth-child(5n+1) a{{color:{link_alt2};}}')

  return f'''<style>
body{{background:{palette['bg']};color:{palette['fg']};font-family:{body_font};}}
h1{{font-family:{h1_font};color:{palette['fg']};}}
h1 + .sub{{color:{palette['dim']};font-family:{random.choice(FONTS)};}}
h2{{font-family:{h2_font};color:{palette['accent']};}}
h3{{font-family:{h3_font};color:{palette['dim']};}}
a{{color:{palette['link']};}}
a:hover{{color:{palette['linkh']};}}
.glyph{{color:{palette['dim']};}}
.rite{{color:{palette['accent']};}}
.flag{{color:{palette['linkh']};background:{palette['bg']};border-color:{palette['accent']};}}
::selection{{background:{palette['accent']};color:{palette['linkh']};}}
hr{{color:{palette['dim']};}}
{chr(10).join(rules)}
</style>'''

def page_shell(title, palette, body_inner):
  return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title} &mdash; lhohq</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" href="data:,">
<link rel="stylesheet" href="/style.css">
{page_style(palette, 0)}
</head><body>
<div class="noise"></div><div class="scan"></div><div class="vignette"></div>
<main>
{body_inner}
</main></body></html>
'''

# ────────────────────────── DISTRACTOR PAGE ──────────────────────────

def gen_distractor(name):
  palette = random.choice(PALETTES)
  pool = [r for r in DISTRACTORS if r != name]
  subtitle = random.choice(SUBTITLES)
  glyph_str = ' &nbsp; '.join(random.sample(GLYPHS, k=3))
  intro = f'<p class="cormorant center">{random.choice([
    f"a {name} is a room which has been asked to apologise for itself.",
    f"the {name} is what remains when the rest is no longer welcome.",
    f"in the {name}, the question becomes the answer becomes the question.",
    f"the {name} is older than its purpose, and has, on the whole, outlived it.",
    f"to be in the {name} is to be slightly elsewhere from yourself.",
    f"the {name} keeps what is given. the {name} gives nothing back.",
    f"what enters the {name} does not, strictly speaking, leave it.",
    f"a {name} is a confession the house has agreed to keep on its behalf.",
    f"the {name} is the part of the house the house declines to discuss.",
  ])}</p>'

  n_paras = random.randint(11, 17)
  paragraphs = [make_paragraph(pool) for _ in range(n_paras)]
  # insert a huge aside at a random position
  paragraphs.insert(random.randint(2, n_paras-2), make_huge_aside())
  # maybe insert an h2 heading
  if random.random() < 0.7:
    headings = [
      'on the colour of the walls','on the door which is not on the door','on the caretaker',
      'on the visitors who did not return','i. the noted','ii. the unnoted','iii. on departure',
      'a partial account','what the room is for','what the room is not for','an aside',
      'the inventory','on the lighting','on the air',
    ]
    paragraphs.insert(random.randint(3, n_paras-3), f'<h2>{random.choice(headings)}</h2>')
  if random.random() < 0.5:
    paragraphs.insert(random.randint(4, n_paras-2), f'<h2>{random.choice(["a second aside","a note from the caretaker","supplemental","a further matter","by way of conclusion"])}</h2>')
  # second huge aside maybe
  if random.random() < 0.35:
    paragraphs.insert(random.randint(2, n_paras-2), make_huge_aside())
  # SVG eye sometimes
  if random.random() < 0.35:
    paragraphs.insert(1, random_eye_svg(palette['dim']))

  body_inner = f'''
<h1>{name}</h1>
<span class="sub">{subtitle}</span>
<span class="glyph l">{glyph_str}</span>
{intro}
<hr>
{''.join(paragraphs)}
<hr>
{make_map_section(pool, n=random.randint(28,42))}
<p class="tiny faint center">{random.choice(FOOTERS)}</p>
'''
  return page_shell(name, palette, body_inner)

# ────────────────────────── GOLDEN PAGES ──────────────────────────

def gen_index():
  """golden 0. HTML comment hints at robots.txt → /atrium/."""
  palette = random.choice(PALETTES)
  pool = list(DISTRACTORS)
  subtitle = "the house of hollow houses"
  glyph_str = ' &nbsp; '.join(random.sample(GLYPHS, k=3))

  # Build prose where one paragraph contains the real /atrium/ link
  n_paras = 14
  paragraphs = [make_paragraph(pool) for _ in range(n_paras)]
  # inject the atrium link in the middle, naturally
  inject_at = random.randint(5, n_paras-3)
  paragraphs[inject_at] = f'<p>The obedient have always been answered first, and the answer issued to them is a catalogue, organised alphabetically, of every place the {linked("atrium", "atrium")} is not. The catalogue is, by long custom, kept at the front gate, in a small text file the house permits to be read by anyone who knows to ask for it. <em>It is, of course, a complete list.</em></p>'

  # other "noise" paragraphs
  paragraphs.insert(random.randint(2, 5), make_huge_aside())
  paragraphs.insert(2, '<h2>i. on entering</h2>')
  paragraphs.insert(random.randint(6, 10), '<h2>ii. on the obedient</h2>')
  paragraphs.insert(2, random_eye_svg(palette['dim']))

  body_inner = f'''
<!--
  the obedient ask the robots first. the rest read the walls.
  every word is a door. most doors are walls pretending.
-->
<h1>lhohq</h1>
<span class="sub">{subtitle}</span>
<span class="glyph l">{glyph_str}</span>
<p class="cormorant center">you have arrived at a place that was not waiting for you.</p>
<hr>
{''.join(paragraphs)}
<hr>
{make_map_section(pool, n=40)}
<p class="warn center breathe" style="opacity:.7;">the house thanks you for your visit. the house has already forgotten you.</p>
<p class="tiny faint center">est. <span class="reflected">MCMXLIV</span> &nbsp;&middot;&nbsp; visitor no. 8 4 4 1 3 &nbsp;&middot;&nbsp; the caretaker is elsewhere</p>
'''
  return page_shell("lhohq", palette, body_inner)

def gen_atrium():
  """golden 1. CSS-hidden letters spell OSSUARY. real link to /ossuary/."""
  palette = random.choice(PALETTES)
  pool = list(DISTRACTORS)
  subtitle = "the first chamber of the hollow house"
  glyph_str = ' &nbsp; '.join(random.sample(GLYPHS, k=3))

  # The puzzle: 7 paragraphs whose first character is wrapped in <span class="h"> spelling OSSUARY
  hidden_letters = list("OSSUARY")
  puzzle_paragraphs = []
  hint_lines = [
    "ften the visitors look only at what shines. They are escorted, gently, back to the threshold, and the house arranges for them to remember nothing of the visit.",
    "ometimes a word holds another word inside it, the way a coffin holds a coffin, the way a room holds a room.",
    "elect what you cannot see. This is the instruction the house gives most often, and which the visitors most often decline.",
    "nder every floor is a floor. Under that floor is a name. Under the name is the person the name once belonged to.",
    "sk the room what it is, and the room, on a good day, will tell you. Ask politely. Ask in lower case.",
    "ooms are not buildings. Rooms are sentences. You are reading one now.",
    "ou are nearly through. The next chamber is named for what we keep when there is nothing else left.",
  ]
  for i, ltr in enumerate(hidden_letters):
    line = hint_lines[i]
    p = f'<p><span class="h">{ltr}</span>{line}</p>'
    puzzle_paragraphs.append(p)

  # noise prose
  n_noise = 10
  noise_paras = [make_paragraph(pool) for _ in range(n_noise)]
  noise_paras.insert(random.randint(1,3), make_huge_aside())
  noise_paras.insert(random.randint(1,4), '<h2>ii. on the colour of the walls</h2>')

  # Real /ossuary/ link — inject in a final closing paragraph among noise
  closing = f'<p>You are looking for a name. The name is a place. The name is hidden in this room, in a colour the walls were not, on the whole, painted in. When you have read the walls correctly, the name will appear among the {linked("ossuary", "ossuary")} you have already been shown, and you will know which door to take.</p>'

  # h2 for the puzzle section
  puzzle_block = '<h2>i. on the colour of the walls</h2>' + ''.join(puzzle_paragraphs)

  body_inner = f'''
<!-- not every word is the colour it appears to be. select all, if you must. -->
<h1>atrium</h1>
<span class="sub">{subtitle}</span>
<span class="glyph l">{glyph_str}</span>
{random_eye_svg(palette['dim'])}
<p class="cormorant center">the obedient have been answered. the rest are now obliged to read.</p>
<hr>
{noise_paras[0]}
{noise_paras[1]}
{noise_paras[2]}
{puzzle_block}
{noise_paras[3]}
{noise_paras[4]}
{noise_paras[5]}
{noise_paras[6]}
{noise_paras[7]}
{noise_paras[8]}
{noise_paras[9]}
{closing}
<hr>
{make_map_section(pool, n=36)}
<p class="tiny faint center">est. <span class="reflected">MCMXLIV</span> &nbsp;&middot;&nbsp; visitor no. <span class="flicker">8 4 4 1 3</span></p>
'''
  return page_shell("atrium", palette, body_inner)

def gen_ossuary():
  """golden 2. base64 puzzle → 'what the mirror sees, the mirror keeps' → /mirror/."""
  palette = random.choice(PALETTES)
  pool = list(DISTRACTORS)
  subtitle = "the library of those who stopped reading"
  glyph_str = ' &nbsp; '.join(random.sample(GLYPHS, k=3))

  rite_plain = b"what the mirror sees, the mirror keeps"
  rite_b64 = base64.b64encode(rite_plain).decode()

  n_paras = 10
  paragraphs = [make_paragraph(pool) for _ in range(n_paras)]
  paragraphs.insert(random.randint(1,3), make_huge_aside())
  paragraphs.insert(2, '<h2>i. the rite</h2>')
  paragraphs.insert(5, f'<code class="rite breathe">{rite_b64}</code>')
  paragraphs.insert(7, '<h2>ii. the catalogue</h2>')

  closing = f'<p>The rite, on decoding, is a sentence. The sentence contains a noun. The noun is the name of the next room. The noun appears, somewhere on this page, among the {linked("mirror", "mirror")} of other words, and is, in the manner of the house, indistinguishable from them.</p>'

  body_inner = f'''
<h1>ossuary</h1>
<span class="sub">{subtitle}</span>
<span class="glyph l">{glyph_str}</span>
<p class="cormorant center">every bone is a sentence the body finally agreed to stop revising.</p>
<hr>
{''.join(paragraphs)}
{closing}
<hr>
{make_map_section(pool, n=36)}
<p class="tiny faint center">sixty-four letters in the alphabet of refusal. one room in the answer.</p>
'''
  return page_shell("ossuary", palette, body_inner)

def gen_mirror():
  """golden 3. all text reversed via scaleX(-1). reveals 'wellspring'."""
  palette = random.choice(PALETTES)
  pool = list(DISTRACTORS)
  subtitle = "the room that opens only when you stop looking"
  glyph_str = ' &nbsp; '.join(random.sample(GLYPHS, k=3))

  n_paras = 10
  paragraphs = [make_paragraph(pool) for _ in range(n_paras)]
  paragraphs.insert(random.randint(1,3), make_huge_aside())
  paragraphs.insert(2, '<h2>i. on the silvering</h2>')
  paragraphs.insert(6, '<h2>ii. on the next chamber</h2>')

  # explicit reveal in prose
  reveal = f'<p>The next chamber is called the {linked("wellspring", "wellspring")}. It lies beneath this one, in a sense that has nothing to do with elevation. Knock once, in lower case. Enter. Do not speak above the water.</p>'

  # extra mirror-styled paragraph
  body_inner = f'''
<style>
  main > *:not(h1):not(.sub):not(.glyph):not(hr){{transform:scaleX(-1);}}
</style>
<h1>mirror</h1>
<span class="sub">{subtitle}</span>
<span class="glyph l breathe">{glyph_str}</span>
<p class="cormorant center">a mirror is a door which has agreed, for the duration of your attention, to pretend to be a wall.</p>
<hr>
{''.join(paragraphs)}
{reveal}
<hr>
{make_map_section(pool, n=34)}
<p class="tiny faint center">the mirror thanks you. the mirror, in fact, has thanked you, slightly before you arrived.</p>
'''
  return page_shell("mirror", palette, body_inner)

def gen_wellspring():
  """golden 4. cream-and-black gothic page. morse hidden in spaces of an elegy.
     decodes to: THE FLAG LIES WAITING IN THE SANCTUM
     gap convention: 1 space = dot, 3 spaces = dash, line break = letter sep, blank line = word sep."""
  pool = list(DISTRACTORS)

  # the elegy. each line = one morse letter (encoded by space widths between words).
  # verified letter-by-letter against THE FLAG LIES WAITING IN THE SANCTUM.
  poem = (
    "come   back\n"                          # T (-)
    "the moon does not turn\n"               # H (....)
    "no longer\n"                            # E (.)
    "\n"
    "petals fall where she   walked\n"       # F (..-.)
    "hold what   was given gently\n"         # L (.-..)
    "wind across   water\n"                  # A (.-)
    "all   is   done already\n"              # G (--.)
    "\n"
    "lift this   stone from heart\n"         # L (.-..)
    "you are still\n"                        # I (..)
    "always there\n"                         # E (.)
    "ash bone breath dust\n"                 # S (...)
    "\n"
    "we who   walked   together\n"           # W (.--)
    "and yet   parted\n"                     # A (.-)
    "the road bends\n"                       # I (..)
    "press   onward\n"                       # T (-)
    "leaves under foot\n"                    # I (..)
    "snow   on shoulders\n"                  # N (-.)
    "winter   pulls   the world\n"           # G (--.)
    "\n"
    "where you went\n"                       # I (..)
    "down   below knowing\n"                 # N (-.)
    "\n"
    "come   home\n"                          # T (-)
    "the cold air keeps walking\n"           # H (....)
    "without you\n"                          # E (.)
    "\n"
    "stars fall in silence\n"                # S (...)
    "into the   river\n"                     # A (.-)
    "drowned   in light\n"                   # N (-.)
    "below   the silence   below silence\n"  # C (-.-.)
    "speak   gently\n"                       # T (-)
    "what was once   ours\n"                 # U (..-)
    "always   never   here"                  # M (--)
  )

  # the answer "sanctum" lives among 22 other room links in a passages strip — the player
  # has to decode the morse to know which word to look for. styled identically to noise.
  passage_rooms = random.sample(pool, k=22) + ['sanctum']
  random.shuffle(passage_rooms)
  passages_html = ', '.join(f'the <a href="/{r}/">{r}</a>' for r in passage_rooms)

  return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>wellspring &mdash; lhohq</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" href="data:,">
<link rel="stylesheet" href="/style.css">
<style>
  /* — gothic parchment skin: cream and ink only — */
  html,body{{background:#efe5d0;color:#0a0a0a;}}
  body{{font-family:"Old Standard TT","EB Garamond",Georgia,serif;font-size:17px;line-height:1.78;}}
  main{{max-width:560px;margin:0 auto;padding:11vh 6vw 16vh;}}
  /* kill the dark overlays inherited from base */
  .scan,.vignette,.noise{{display:none !important;}}

  h1{{font-family:"UnifrakturCook",serif;font-weight:700;font-size:68px;color:#0a0a0a;
     text-align:center;margin:0 0 1vh;letter-spacing:.01em;line-height:1;text-transform:lowercase;}}
  h1 + .sub{{display:block;text-align:center;font-family:"Cormorant Garamond",serif;font-style:italic;
            font-size:13px;letter-spacing:.42em;color:#3a2a1a;margin:0 0 11vh;text-transform:lowercase;}}
  hr{{border:0;border-top:1px solid #0a0a0a;opacity:.22;width:40%;margin:9vh auto;}}
  a{{color:#1a1a1a;text-decoration:none;border-bottom:1px dotted #6a5a4a;}}
  a:hover{{color:#000;border-bottom-color:#000;}}
  ::selection{{background:#0a0a0a;color:#efe5d0;}}

  /* — the elegy: no box, no border, just typewriter prose centred on the page — */
  .elegy{{
    display:block;
    margin:0 auto;
    padding:0;
    font-family:"Special Elite","Courier New",monospace;
    font-size:15px;
    line-height:2.3;
    letter-spacing:.14em;
    color:#0a0a0a;
    white-space:pre;
    text-align:center;
    word-break:normal;
  }}

  .passages{{font-family:"EB Garamond",serif;font-size:13px;line-height:1.95;text-align:center;
            color:#2a1a0a;column-count:2;column-gap:2.4em;}}
</style>
</head>
<body>
<main>
  <h1>wellspring</h1>
  <span class="sub">a quiet mouth in the floor of the world</span>

  <pre class="elegy">{poem}</pre>

  <hr>

  <p class="passages">{passages_html}.</p>
</main>
</body></html>
'''

def gen_sanctum():
  """golden 5. final flag."""
  palette = random.choice(PALETTES)
  pool = list(DISTRACTORS)
  subtitle = "the last room the house has agreed to admit"
  glyph_str = ' &nbsp; '.join(random.sample(GLYPHS, k=3))

  n_paras = 6
  paragraphs = [make_paragraph(pool) for _ in range(n_paras)]
  paragraphs.insert(random.randint(1,3), make_huge_aside())

  body_inner = f'''
<h1>sanctum</h1>
<span class="sub">{subtitle}</span>
<span class="glyph l breathe">{glyph_str}</span>
<p class="cormorant center">you have walked through robots, and under near-invisible letters, and across a sixty-four-character rite, and into a mirror, and down a half-turned alphabet, and arrived here.</p>
<hr>
{paragraphs[0]}
{paragraphs[1]}
{paragraphs[2]}
<h2>the artifact</h2>
<p>What follows is what you came for. The house parts with it without regret. The house, in any case, has more of everything than it has need of.</p>
<p class="center">
  <span class="flag breathe">csaw{{w4nd3r3r_0f_th3_h0ll0w_h0us3}}</span>
</p>
{paragraphs[3]}
{paragraphs[4]}
{paragraphs[5]}
<hr>
{make_map_section(pool, n=24)}
<p class="cormorant center" style="margin-top:6vh;">the house thanks you for your visit. the house has, in the strictest sense, already forgotten you.</p>
<script>
console.log("%c the house remembers what the mirror keeps. ", "color:#bdb1a0;background:#000;font-family:serif;font-size:14px;padding:6px 12px;");
</script>
'''
  return page_shell("sanctum", palette, body_inner)

# ────────────────────────── WRITE ALL ──────────────────────────

def write(path, content):
  full = os.path.join(ROOT, path)
  os.makedirs(os.path.dirname(full) if os.path.dirname(full) else ROOT, exist_ok=True)
  with open(full, 'w', encoding='utf-8') as f:
    f.write(content)

def main():
  # robots.txt
  write('robots.txt', "User-agent: *\nDisallow: /atrium/\n\n# the obedient have been answered.\n")

  # golden path
  write('index.html', gen_index())
  write('atrium/index.html', gen_atrium())
  write('ossuary/index.html', gen_ossuary())
  write('mirror/index.html', gen_mirror())
  write('wellspring/index.html', gen_wellspring())
  write('sanctum/index.html', gen_sanctum())

  # distractors
  for name in DISTRACTORS:
    write(f'{name}/index.html', gen_distractor(name))

  total = 1 + len(GOLDEN) + len(DISTRACTORS)
  print(f"wrote {total} pages (1 index + {len(GOLDEN)} golden + {len(DISTRACTORS)} distractors)")

if __name__ == "__main__":
  main()
