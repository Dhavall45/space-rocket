import streamlit as st
import numpy as np
import time
import random

# Game parameters
GRID_WIDTH = 40
GRID_HEIGHT = 20
PLAYER_CHAR = 'A'
ALIEN_CHAR = 'V'
MISSILE_CHAR = '|'
ALIEN_MISSILE_CHAR = '!'
EXPLOSION_CHAR = 'X'
EMPTY_CHAR = '.'

# Game state initialization
def initialize_game_state():
    return {
        'player_pos': GRID_WIDTH // 2,
        'aliens': [(5, 5 + i * 3) for i in range(5)], # (row, col)
        'missiles': [], # [(row, col), ...]
        'alien_missiles': [], # [(row, col), ...]
        'score': 0,
        'game_over': False,
        'direction': 'right', # for alien movement
        'alien_move_counter': 0,
        'alien_move_frequency': 5, # aliens move every X frames
        'explosion_timer': {}, # {(row, col): timer_start_time}
        'current_key_down': None # Store the key currently being held down (from JS)
    }

def draw_grid(game_state):
    grid = np.full((GRID_HEIGHT, GRID_WIDTH), EMPTY_CHAR, dtype=str)

    # Draw player
    grid[GRID_HEIGHT - 2, game_state['player_pos']] = PLAYER_CHAR

    # Draw aliens
    for r, c in game_state['aliens']:
        if 0 <= r < GRID_HEIGHT and 0 <= c < GRID_WIDTH:
            grid[r, c] = ALIEN_CHAR

    # Draw missiles
    for r, c in game_state['missiles']:
        if 0 <= r < GRID_HEIGHT and 0 <= c < GRID_WIDTH:
            grid[r, c] = MISSILE_CHAR
            
    # Draw alien missiles
    for r, c in game_state['alien_missiles']:
        if 0 <= r < GRID_HEIGHT and 0 <= c < GRID_WIDTH:
            grid[r, c] = ALIEN_MISSILE_CHAR

    # Draw explosions
    explosions_to_remove = []
    for (r, c), start_time in game_state['explosion_timer'].items():
        if time.time() - start_time < 0.2: # Show explosion for a short duration
            if 0 <= r < GRID_HEIGHT and 0 <= c < GRID_WIDTH:
                grid[r, c] = EXPLOSION_CHAR
        else:
            explosions_to_remove.append((r,c)) # Mark for removal
            
    for exp_pos in explosions_to_remove:
        del game_state['explosion_timer'][exp_pos]

    return "\n".join(["".join(row) for row in grid])

def update_game_state(game_state, action=None): # 'action' can be 'left', 'right', 'shoot', or None
    if game_state['game_over']:
        return game_state

    # Player movement (priority to button presses, then keyboard)
    if action == 'left' or game_state['current_key_down'] == "ArrowLeft":
        game_state['player_pos'] = max(0, game_state['player_pos'] - 1)
    elif action == 'right' or game_state['current_key_down'] == "ArrowRight":
        game_state['player_pos'] = min(GRID_WIDTH - 1, game_state['player_pos'] + 1)
    
    # Shooting: trigger on 'shoot' action or spacebar keydown
    if action == 'shoot' or game_state['current_key_down'] == " ":
        if len(game_state['missiles']) < 3: # Limit missiles to prevent spamming too many
            game_state['missiles'].append([GRID_HEIGHT - 3, game_state['player_pos']])

    # Missile movement (player)
    new_missiles = []
    for r, c in game_state['missiles']:
        new_r = r - 1
        if new_r >= 0:
            new_missiles.append([new_r, c])
    game_state['missiles'] = new_missiles

    # Alien movement
    game_state['alien_move_counter'] += 1
    if game_state['alien_move_counter'] >= game_state['alien_move_frequency']:
        game_state['alien_move_counter'] = 0
        
        move_down = False
        if game_state['aliens']: # Only move if there are aliens
            max_col = max(alien[1] for alien in game_state['aliens'])
            min_col = min(alien[1] for alien in game_state['aliens'])

            if game_state['direction'] == 'right':
                if max_col >= GRID_WIDTH - 1:
                    move_down = True
                    game_state['direction'] = 'left'
            else: # direction == 'left'
                if min_col <= 0:
                    move_down = True
                    game_state['direction'] = 'right'

        new_aliens = []
        for r, c in game_state['aliens']:
            if move_down:
                new_aliens.append([r + 1, c])
                # Check if aliens reached player's row
                if r + 1 >= GRID_HEIGHT - 2:
                    game_state['game_over'] = True
                    st.session_state.game_state['message'] = "ALIENS REACHED YOU! Game Over!"
            else:
                if game_state['direction'] == 'right':
                    new_aliens.append([r, c + 1])
                else:
                    new_aliens.append([r, c - 1])
        game_state['aliens'] = new_aliens
        
        # Alien shooting (randomly)
        if game_state['aliens'] and random.random() < 0.2: # 20% chance any alien shoots
            shooter_alien = random.choice(game_state['aliens'])
            game_state['alien_missiles'].append([shooter_alien[0] + 1, shooter_alien[1]])


    # Alien missile movement
    new_alien_missiles = []
    for r, c in game_state['alien_missiles']:
        new_r = r + 1
        # Check collision with player *before* adding to new_alien_missiles if it's hitting
        if new_r == GRID_HEIGHT - 2 and c == game_state['player_pos']:
            game_state['game_over'] = True
            st.session_state.game_state['message'] = "YOU WERE HIT! Game Over!"
            game_state['explosion_timer'][(GRID_HEIGHT - 2, game_state['player_pos'])] = time.time() # Player explosion
            # Do NOT add this missile back if it hit the player
        elif new_r < GRID_HEIGHT:
            new_alien_missiles.append([new_r, c])
    game_state['alien_missiles'] = new_alien_missiles

    # Collision detection (missile-alien)
    collisions = [] # Stores (missile_index, alien_index)
    for m_idx, (m_r, m_c) in enumerate(game_state['missiles']):
        for a_idx, (a_r, a_c) in enumerate(game_state['aliens']):
            if m_r == a_r and m_c == a_c:
                collisions.append((m_idx, a_idx))
                game_state['score'] += 10
                game_state['explosion_timer'][(a_r, a_c)] = time.time() # Alien explosion
                break # A missile can only hit one alien, move to next missile

    # Remove hit aliens and missiles
    hit_alien_indices = set()
    hit_missile_indices = set()
    for m_idx, a_idx in collisions:
        hit_alien_indices.add(a_idx)
        hit_missile_indices.add(m_idx)

    game_state['aliens'] = [alien for i, alien in enumerate(game_state['aliens']) if i not in hit_alien_indices]
    game_state['missiles'] = [missile for i, missile in enumerate(game_state['missiles']) if i not in hit_missile_indices]

    # Check if all aliens are defeated
    if not game_state['aliens'] and not game_state['game_over']:
        game_state['game_over'] = True
        st.session_state.game_state['message'] = "YOU DEFEATED ALL ALIENS! You Win!"

    return game_state

# JavaScript for keypress detection
# This version explicitly sets a value on keydown and null on keyup
key_js = """
<script>
const streamlitComponentKey = "st_key_press_component";

document.addEventListener('keydown', function(e) {
    if (['ArrowLeft', 'ArrowRight', ' '].includes(e.key)) {
        // Set the component value to the pressed key
        Streamlit.setComponentValue(e.key);
    }
});

document.addEventListener('keyup', function(e) {
    if (['ArrowLeft', 'ArrowRight', ' '].includes(e.key)) {
        // Only reset if the released key is the one currently being "held" for movement
        // or if it's the spacebar which we want to register as a single press per press
        if (Streamlit.getComponentValue() === e.key || e.key === ' ') {
             Streamlit.setComponentValue(null);
        }
    }
});
</script>
"""

# Main game function
def space_invaders_game():
    st.title("👾 Space Invaders (Text-Based)")
    st.markdown("Use **Left/Right Arrow** keys or **on-screen buttons** to move. Press **Spacebar** or **Shoot button** to fire. Shoot down aliens before they reach you!")

    # Embed the JavaScript for keypress detection
    st.components.v1.html(key_js, height=0, width=0)

    if 'game_state' not in st.session_state or st.session_state.game_state.get('game_over', True):
        st.session_state.game_state = initialize_game_state()
        st.session_state.game_state['message'] = "Press 'New Game' to start!"

    # Game UI elements
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("New Game"):
            st.session_state.game_state = initialize_game_state()
            st.session_state.game_state['message'] = "Game Started!"
            st.rerun() # Rerun to immediately update game state and start loop
    with col2:
        st.metric("Score", st.session_state.game_state['score'])
    with col3:
        st.info(st.session_state.game_state.get('message', ''))

    game_display_placeholder = st.empty() # Placeholder for the game grid

    # --- Add On-Screen Buttons ---
    st.markdown("---")
    st.subheader("Controls:")
    control_cols = st.columns([1, 1, 1]) # Left, Shoot, Right
    
    with control_cols[0]:
        if st.button("⬅️ Left"):
            # Update game state with 'left' action and rerun
            st.session_state.game_state = update_game_state(st.session_state.game_state, action='left')
            st.rerun() # Rerun to process the button press immediately
    
    with control_cols[1]:
        if st.button("🚀 Shoot"):
            # Update game state with 'shoot' action and rerun
            st.session_state.game_state = update_game_state(st.session_state.game_state, action='shoot')
            st.rerun() # Rerun to process the button press immediately

    with control_cols[2]:
        if st.button("➡️ Right"):
            # Update game state with 'right' action and rerun
            st.session_state.game_state = update_game_state(st.session_state.game_state, action='right')
            st.rerun() # Rerun to process the button press immediately
    # --- End On-Screen Buttons ---


    # Game loop
    while not st.session_state.game_state['game_over']:
        # Get the current value from the JavaScript component (for keyboard input)
        key_from_js = st.session_state.get("st_key_press_component", None)
        
        # Update the game_state['current_key_down'] based on JS input
        st.session_state.game_state['current_key_down'] = key_from_js if key_from_js in ["ArrowLeft", "ArrowRight"] else None
        
        # Update game state (no specific action from buttons here, they trigger rerun)
        # This call handles alien/missile movement and any continuous keyboard movement
        st.session_state.game_state = update_game_state(st.session_state.game_state, action=None) # No button action here, it's already handled by rerun
        
        grid_str = draw_grid(st.session_state.game_state)
        game_display_placeholder.code(grid_str, language="text") # Use st.code for monospace font

        time.sleep(0.1) # Game speed

    if st.session_state.game_state['game_over']:
        game_display_placeholder.code(draw_grid(st.session_state.game_state), language="text")
        st.error(st.session_state.game_state.get('message', 'Game Over!'))
        st.balloons()
        
        # Clear the key press history for next game
        st.session_state.game_state['current_key_down'] = None
        
        if st.button("Play Again?", key="play_again_button_after_game_over"):
            st.session_state.game_state = initialize_game_state()
            st.session_state.game_state['message'] = "Game Started! Good luck!"
            st.rerun()

if __name__ == "__main__":
    space_invaders_game()