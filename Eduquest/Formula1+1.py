import pygame, random, os, asyncio, sys, concurrent.futures
from pygame.locals import *
from pygame import mixer
from lmnt.api import Speech
from dotenv import load_dotenv

# Load environment variables and initialize modules
load_dotenv()
pygame.init()
mixer.init()

api_key = os.getenv('LMNT_API_KEY')

# Screen settings
SCREEN_WIDTH, SCREEN_HEIGHT = 1550, 800
DISPLAYSURF = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
font = pygame.font.SysFont("Verdana", 48)
small_font = pygame.font.SysFont("Verdana", 30)
clock = pygame.time.Clock()

# Colors
BLUE, RED, WHITE, BLACK, GREEN = (0, 0, 255), (180, 0, 0), (255, 255, 255), (0, 0, 0), (0, 125, 0)

# Game Variables
PLAYER_MOVE_AMOUNT = 150
FINISH_LINE = SCREEN_WIDTH - 200
DIFFICULTY = 1
AUDIO_ON = False  # Set to True if you want audio

# Assets
race_track = pygame.image.load('racetrack.png')
player_img = pygame.image.load('red_car.png')
opp_img = pygame.image.load('blue_car.png')
bg_music = pygame.mixer.Sound('moonlightdrive.mp3')
player_sfx = pygame.mixer.Sound('car-passing.mp3')

# Fonts
font = pygame.font.SysFont("Verdana", 40)
font_small = pygame.font.SysFont("Verdana", 20)
winner_text = font.render("", True, BLACK)

# Game States
home_screen = True
operation_type = None  # This will store "addition", "subtraction", or "both"
game_over = False

# Initialize a ThreadPoolExecutor
executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

# CLASSES
class Button:
    def __init__(self, name, x_pos, y_pos):
        self.name = name
        self.x_pos, self.y_pos = x_pos, y_pos
        self.surface = pygame.Surface((300, 100))
        self.surface.fill((235, 216, 189))
        self.rect = pygame.Rect(x_pos, y_pos, 300, 100)
        self.surface_rect = self.surface.get_rect(topleft=(self.x_pos, self.y_pos))

    def create_text(self):
        # Render the text on top of the button surface
        text = font.render(self.name, True, (0, 0, 0), (235, 216, 189))
        text_rect = text.get_rect(center=(self.surface.get_width()/2, self.surface.get_height()/2))
        self.surface.blit(text, text_rect)

    def render(self, screen, text=""):
        text_surface = font.render(f"{text or self.name}", True, BLACK)
        text_rect = text_surface.get_rect(center=(150, 50))
        self.surface.blit(text_surface, text_rect)
        screen.blit(self.surface, (self.x_pos, self.y_pos))

class Question(Button):
    # size 600x100
    surface = pygame.image.load('question.png')

    def __init__(self, text, x_pos, y_pos):
        super().__init__(text, x_pos, y_pos)  # Use text as name
        self.create_text()  # Create text on initialization

    def create_text(self):
        text_surface = font.render(self.name, True, (0, 0, 0), (235, 216, 189))
        text_rect = text_surface.get_rect(center=(self.surface.get_width()/2, self.surface.get_height()/2))
        self.surface.blit(text_surface, text_rect)



# HELPER FUNCTIONS
def generate_and_play_audio(question_text):
    async def _generate_audio():
        async with Speech(api_key=api_key) as speech:
            synthesis = await speech.synthesize(question_text, 'lily')
        audio_filename = f"question.mp3"
        with open(audio_filename, 'wb') as f:
            f.write(synthesis['audio'])
        # mixer.music.load("question.mp3")
        # mixer.music.play()

        pygame.mixer.init()

        mp3 = pygame.mixer.Sound(audio_filename)
        mp3.play()

    # Run the async function _generate_audio in the event loop
    asyncio.run(_generate_audio())

async def generate_question(operation_type):
    global game_over  # Access global game state
    if game_over:     # Avoid question generation if the game is over
        return None, None

    num1, num2 = random.randint(1, 10), random.randint(1, 10)
    
    def addition():
        question = f"{num1} + {num2}?"
        lmnt_text = f"{num1} + {num2}?"
        answer = num1 + num2
        return question, answer, lmnt_text

    def subtraction():
        question = f"{max(num1, num2)} - {min(num1, num2)} = ?"
        lmnt_text = f"{max(num1, num2)} - {min(num1, num2)}?"
        answer = max(num1, num2) - min(num1, num2)
        return question, answer, lmnt_text

    if operation_type == "addition":
        question_text, correct_answer, lmnt_text = addition()
    elif operation_type == "subtraction":
        question_text, correct_answer, lmnt_text = subtraction()
    else:
        question_text, correct_answer, lmnt_text = random.choice([addition, subtraction])()

    # Handle audio generation in a background thread only if the game is not over
    if AUDIO_ON and not game_over:
        executor.submit(generate_and_play_audio, lmnt_text)
    
    # print("LOG GENERATE QUESTION CALLED", question_text)
    return question_text, correct_answer

def generate_buttons(question_text, correct_answer):
    question_btn = Question(question_text, 625, 25)

    answer_btn_positions = [(375, 135), (875, 135), (375, 250), (875, 250)]
    answer_btns = [Button(i, x, y) for i, (x, y) in enumerate(answer_btn_positions, 1)]
    answer_options = [correct_answer, correct_answer + 1, correct_answer - 1, correct_answer + 2]
    random.shuffle(answer_options)  # randomize answer button
    # dictionary with key as button and value as the text it should hold
    answer_btns_dict = {b: a for b, a in zip(answer_btns, answer_options)}

    return question_btn, answer_btns_dict

async def game_loop():
    global game_over, home_screen, operation_type, DIFFICULTY

    # Set initial positions and variables
    player_x_pos, opp_x_pos = 60, 40
    feedback = ""
    target_x_pos = player_x_pos
    is_moving = False

    # Generate the initial question
    question_text, correct_answer = await generate_question(operation_type)
    question_btn, answer_btns_dict = generate_buttons(question_text, correct_answer)

    # Endgame buttons for replay and exit
    play_again_btn = Button("Play Again", SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 150)
    exit_btn = Button("Exit", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 150)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_over:
                    if play_again_btn.rect.collidepoint(event.pos):
                        # Reset the game state for a fresh start
                        game_over = False
                        home_screen = True
                        operation_type = None
                        DIFFICULTY = 1
                        await main()  # Restart from main menu
                    elif exit_btn.rect.collidepoint(event.pos):
                        pygame.quit()
                        sys.exit()
                else:
                    # Handle answer button clicks during active gameplay
                    for btn in answer_btns_dict.keys():
                        if btn.rect.collidepoint(event.pos):
                            if answer_btns_dict[btn] == correct_answer:
                                # Check if the next move would cross the finish line
                                if player_x_pos + PLAYER_MOVE_AMOUNT >= FINISH_LINE:
                                    target_x_pos = FINISH_LINE
                                    is_moving = True
                                    game_over = True
                                    feedback = "Player Wins!"
                                else:
                                    target_x_pos = player_x_pos + PLAYER_MOVE_AMOUNT
                                    is_moving = True
                                    feedback = ""  # Only reset feedback if game isn't ending
                                    # Only generate new question if game isn't ending
                                    question_text, correct_answer = await generate_question(operation_type)
                                    question_btn, answer_btns_dict = generate_buttons(question_text, correct_answer)
                                break
                            else:
                                
                                btn.visible = False
                                feedback = "Incorrect! Try Again."

                                

        # Move players if game isn't over
        if not game_over:
            if is_moving:
                player_sfx.play()
                move_amount = 10
                player_x_pos += move_amount
                if player_x_pos >= target_x_pos:
                    player_x_pos = target_x_pos
                    is_moving = False
            
            opp_x_pos += DIFFICULTY

            # Check if opponent wins
            if opp_x_pos >= FINISH_LINE:
                game_over = True
                feedback = "Opponent Wins!"

        # Display track and player positions
        screen.blit(race_track, (0, 0))
        screen.blit(opp_img, (opp_x_pos, 535))
        screen.blit(player_img, (player_x_pos, 587))

        # Display the question and answers only if game isn't over
        if not game_over:
            question_btn.create_text()
            screen.blit(question_btn.surface, (question_btn.x_pos, question_btn.y_pos))
            for btn in answer_btns_dict.keys():
                btn.render(screen, text=str(answer_btns_dict[btn]))

        # Display feedback and endgame options if game is over
        
        if "Player Wins!" or "Try Again." in feedback:
            text_height, text_width = 0, 0
            if "Player Wins!" in feedback:
                text_width = SCREEN_WIDTH // 2 - 130
                text_height = SCREEN_HEIGHT // 2 - 235
                pygame.draw.rect(screen, (235, 216, 189), pygame.Rect(575, text_height - 30, 400, 100))
                feedback_surface = font.render(feedback, True, GREEN)
            elif "Opponent Wins" in feedback:
                text_width = SCREEN_WIDTH // 2 - 160
                text_height = SCREEN_HEIGHT // 2 - 235
                pygame.draw.rect(screen, (235, 216, 189), pygame.Rect(575, text_height - 30, 400, 100))
                feedback_surface = font.render(feedback, True, RED)
            else:
                text_width = SCREEN_WIDTH // 2 - 150
                text_height = SCREEN_HEIGHT // 2 - 8
                feedback_surface = small_font.render(feedback, True, RED)

            screen.blit(feedback_surface, (text_width, text_height))


        if game_over:
            play_again_btn.render(screen)
            exit_btn.render(screen)

        pygame.display.update()
        clock.tick(60)

def menu():
    global home_screen, operation_type, DIFFICULTY

    race_track = pygame.image.load('racetrack.png')  # Background image
    player = pygame.image.load('red_car.png')
    player_x_pos = 60
    opp = pygame.image.load('blue_car.png')
    opp_x_pos = 40

    buttonQ = Question('START', 575, 150)
    buttons = [buttonQ]

    difficulty_buttons = [
        Button('Easy', 150, 150),
        Button('Medium', 570, 150),
        Button('Hard', 990, 150)
    ]

    question_buttons = [
        Button('Addition', 150, 150),
        Button('Subtraction', 570, 150),
        Button('Both', 990, 150)
    ]

    game_state = 'menu'  # Track current state

    while home_screen:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_state == 'menu':
                    for button in buttons:
                        if button.surface_rect.collidepoint(event.pos):
                            game_state = 'difficulty'  # Switch to difficulty selection
                    print("DIFFICULTY")
                elif game_state == 'difficulty':
                    for button in difficulty_buttons:
                        if button.surface_rect.collidepoint(event.pos):
                            if button.name == "Easy":
                                DIFFICULTY = 1
                            elif button.name == "Medium":
                                DIFFICULTY = 2
                            else:
                                DIFFICULTY = 3
                            game_state = 'questions'  # Switch to question selection
                    print("DIFFICULTY", DIFFICULTY)
                elif game_state == 'questions':
                    for button in question_buttons:
                        if button.surface_rect.collidepoint(event.pos):
                            operation_type = button.name.lower()
                            home_screen = False
                    print(operation_type)


        # Draw background
        screen.blit(race_track, (0, 0))

        # Render based on the current state
        if game_state == 'menu':
            screen.blit(opp, (opp_x_pos, 535))
            screen.blit(player, (player_x_pos, 587))

            for button in buttons:
                button.create_text()
                screen.blit(button.surface, (button.x_pos, button.y_pos))

        elif game_state == 'difficulty':
            for button in difficulty_buttons:
                button.create_text()
                screen.blit(button.surface, (button.x_pos, button.y_pos))

        elif game_state == 'questions':
            for button in question_buttons:
                button.create_text()
                screen.blit(button.surface, (button.x_pos, button.y_pos))

        pygame.display.update()
        clock.tick(60)

async def main():
    # Check if the API key was loaded correctly
    #if not api_key:
    #    raise ValueError("LMNT_API_KEY not found. Please make sure it's set in your .env file.")
    
    # Start music loop
    bg_music.set_volume(0.2)
    bg_music.play(loops = -1)
    # Run home screen to choose math operation and difficulty
    menu()

    # After selection, start the game loop
    await game_loop()

asyncio.run(main())