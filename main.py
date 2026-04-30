import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import RadioButtons, Slider, Button
import numpy as np

# Apply Matplotlib's built-in dark theme
plt.style.use('dark_background')

# ==========================================
# CONFIGURATION PARAMETERS
# ==========================================
NUM_NODES = 75              
RANDOM_SEED = 42            
SPACE_SIZE = 10.0           
CONNECTION_RANGE = 2.0      
MAX_PROBABILITY = 0.85      

MIN_NODE_DIST = 0.5         

INIT_SPREAD_SPEED = 0.25         
INIT_SPREAD_POWER = 0.85         
INIT_DECAY_RATE = 0.98           
INIT_DEATH_CHANCE = 0.02    

GROWTH_CHANCE = 0.10        

SNAP_TO_ZERO = 0.05         
ANIMATION_INTERVAL = 50     
CLICK_THRESHOLD = SPACE_SIZE * 0.05 

NODE_SIZE = 250             
EDGE_ALPHA_BASE = 0.15      
EDGE_ALPHA_ACTIVE = 0.90    
BASE_COLOR = np.array([0.35, 0.35, 0.35]) 
BG_COLOR = '#111111' 
BG_COLOR_RGB = np.array([0.067, 0.067, 0.067]) 
DEAD_COLOR = np.array([1.0, 0.0, 0.0])         
FLASH_COLOR = np.array([0.2, 1.0, 0.2])     
GRADIENT_LAYERS = 6         
# ==========================================

# 1. Initialize the Spatial Graph
G = nx.Graph()
G.add_nodes_from(range(NUM_NODES))
np.random.seed(RANDOM_SEED)

pos = {}
for i in range(NUM_NODES):
    for attempt in range(100): 
        new_pos = np.random.uniform(0.5, SPACE_SIZE - 0.5, 2)
        if all(np.linalg.norm(new_pos - pos[j]) >= MIN_NODE_DIST for j in pos):
            pos[i] = new_pos
            break
    else:
        pos[i] = new_pos 

for u in range(NUM_NODES):
    for v in range(u + 1, NUM_NODES):
        dist = np.linalg.norm(pos[u] - pos[v])
        # FIX: Hard cutoff so nodes don't form invisible cross-map connections
        if dist < CONNECTION_RANGE * 1.5:
            probability = np.exp(-dist / (CONNECTION_RANGE * 0.5)) * MAX_PROBABILITY
            if np.random.rand() < probability:
                G.add_edge(u, v)

islands = list(nx.isolates(G))
G.remove_nodes_from(islands)
for node in islands:
    del pos[node]
NUM_NODES = len(G.nodes) 

edge_indices = [(list(G.nodes()).index(u), list(G.nodes()).index(v)) for u, v in G.edges()]
num_edges = len(edge_indices)

active_waves = []
dragging_node = None 

is_dead = np.zeros(NUM_NODES, dtype=bool)
death_state = np.zeros(NUM_NODES) 
flash_state = np.zeros(NUM_NODES) 

growth_active = False

# 2. Setup the Plot and UI
fig, ax = plt.subplots(figsize=(11, 7)) 
fig.canvas.manager.set_window_title('Interactive Social Network')

fig.patch.set_facecolor(BG_COLOR)
ax.set_facecolor(BG_COLOR)
ax.set_title("Social Network (Gossip, Virus, & Growth)", color='white', pad=15)
ax.axis('off')
ax.set_xlim(-1, SPACE_SIZE + 1)
ax.set_ylim(-1, SPACE_SIZE + 1)

fig.subplots_adjust(left=0.35)

ax_tools = plt.axes([0.05, 0.75, 0.20, 0.15], facecolor=BG_COLOR)
ax_tools.set_title('Interaction Tools', color='white', pad=10)
radio = RadioButtons(ax_tools, ('Gossip', 'Virus', 'Move Only')) 

try:
    radio.set_activecolor('#aaaaaa')
except AttributeError:
    radio.activecolor = '#aaaaaa' 

current_tool = 'Gossip'

ax_speed = plt.axes([0.10, 0.55, 0.15, 0.03], facecolor=BG_COLOR)
ax_power = plt.axes([0.10, 0.45, 0.15, 0.03], facecolor=BG_COLOR)
ax_decay = plt.axes([0.10, 0.35, 0.15, 0.03], facecolor=BG_COLOR)
ax_death = plt.axes([0.10, 0.25, 0.15, 0.03], facecolor=BG_COLOR) 
ax_growth = plt.axes([0.05, 0.12, 0.20, 0.06])

fig.text(0.15, 0.62, 'Physics Parameters', color='white', ha='center', fontsize=12, fontweight='bold')

slider_speed = Slider(ax_speed, 'Rumor Speed', 0.01, 1.0, valinit=INIT_SPREAD_SPEED)
slider_power = Slider(ax_power, 'Rumor Reach', 0.10, 1.0, valinit=INIT_SPREAD_POWER)
slider_decay = Slider(ax_decay, 'Forget Rate', 0.70, 0.99, valinit=INIT_DECAY_RATE)
slider_death = Slider(ax_death, 'Lethality', 0.0, 0.15, valinit=INIT_DEATH_CHANCE) 
slider_death.ax.set_visible(False)

btn_growth = Button(ax_growth, 'Turn Growth ON', color='#333333', hovercolor='#555555')
btn_growth.label.set_color('white')

def toggle_growth(event):
    global growth_active
    growth_active = not growth_active
    
    if growth_active:
        btn_growth.label.set_text('Turn Growth OFF')
        btn_growth.color = '#552222' 
    else:
        btn_growth.label.set_text('Turn Growth ON')
        btn_growth.color = '#333333'
        
    fig.canvas.draw_idle()

btn_growth.on_clicked(toggle_growth)

def update_tool(label):
    global current_tool
    current_tool = label
    
    if label == 'Virus':
        slider_speed.label.set_text('Infect Rate')
        slider_power.label.set_text('Viral Load')
        slider_decay.label.set_text('Recovery')
        slider_death.ax.set_visible(True)
    elif label == 'Gossip':
        slider_speed.label.set_text('Rumor Speed')
        slider_power.label.set_text('Rumor Reach')
        slider_decay.label.set_text('Forget Rate')
        slider_death.ax.set_visible(False)
        
    fig.canvas.draw_idle() 

radio.on_clicked(update_tool)

initial_edge_colors = np.tile(np.append(BASE_COLOR, EDGE_ALPHA_BASE), (num_edges, 1))
edges = nx.draw_networkx_edges(G, pos, ax=ax, edge_color=initial_edge_colors)

node_layers = []
for i in range(GRADIENT_LAYERS):
    scale = 1.0 - (i / GRADIENT_LAYERS)
    layer_size = NODE_SIZE * (scale ** 1.5)
    layer = nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=[BASE_COLOR] * NUM_NODES,
        node_size=layer_size,
        edgecolors='none',  
        linewidths=0
    )
    node_layers.append(layer)

# 3. Event Handlers
def on_press(event):
    global dragging_node, active_waves
    
    if event.inaxes != ax or event.xdata is None or event.ydata is None:
        return

    click_coords = np.array([event.xdata, event.ydata])
    min_dist = float('inf')
    closest_node = None

    for node_id, coords in pos.items():
        dist = np.linalg.norm(coords - click_coords)
        if dist < min_dist:
            min_dist = dist
            closest_node = node_id

    if closest_node is not None and min_dist < CLICK_THRESHOLD:
        dragging_node = closest_node
        node_idx = list(G.nodes()).index(closest_node)
        
        if is_dead[node_idx]:
            return
            
        if current_tool in ['Gossip', 'Virus']:
            new_wave_state = np.zeros(NUM_NODES)
            new_wave_state[node_idx] = 1.0
            
            if current_tool == 'Virus':
                random_color = np.array([0.6, 1.0, 0.2]) 
                wave_type = 'virus' 
            else:
                random_color = plt.cm.hsv(np.random.rand())[:3] 
                wave_type = 'gossip' 
            
            active_waves.append({
                'state': new_wave_state,
                'color': np.array(random_color),
                'type': wave_type 
            })

def on_motion(event):
    global dragging_node, pos
    if dragging_node is not None and event.xdata is not None and event.ydata is not None:
        pos[dragging_node] = np.array([event.xdata, event.ydata])
        new_offsets = np.array([pos[i] for i in G.nodes()])
        
        for layer in node_layers:
            layer.set_offsets(new_offsets)
        
        edge_segments = np.asarray([(pos[u], pos[v]) for u, v in G.edges()])
        edges.set_segments(edge_segments)

def on_release(event):
    global dragging_node
    dragging_node = None

fig.canvas.mpl_connect('button_press_event', on_press)
fig.canvas.mpl_connect('motion_notify_event', on_motion)
fig.canvas.mpl_connect('button_release_event', on_release)

# 4. Animation Update Function
def update(frame):
    global active_waves, is_dead, death_state, flash_state, NUM_NODES, edge_indices, num_edges, pos

    if growth_active and np.random.rand() < GROWTH_CHANCE:
        new_pos = None
        for attempt in range(50):
            test_pos = np.random.uniform(0.5, SPACE_SIZE - 0.5, 2)
            if all(np.linalg.norm(test_pos - pos[j]) >= MIN_NODE_DIST for j in pos):
                new_pos = test_pos
                break
        
        if new_pos is not None:
            new_node_id = max(G.nodes()) + 1 if G.nodes() else 0
            pos[new_node_id] = new_pos
            G.add_node(new_node_id)
            NUM_NODES += 1
            
            is_dead = np.append(is_dead, False)
            death_state = np.append(death_state, 0.0)
            flash_state = np.append(flash_state, 1.0) 
            
            for wave in active_waves:
                wave['state'] = np.append(wave['state'], 0.0)
                
            for v in list(G.nodes())[:-1]: 
                dist = np.linalg.norm(pos[new_node_id] - pos[v])
                # FIX: Distance hard cutoff applied to growth too
                if dist < CONNECTION_RANGE * 1.5:
                    probability = np.exp(-dist / (CONNECTION_RANGE * 0.5)) * MAX_PROBABILITY
                    if np.random.rand() < probability:
                        G.add_edge(new_node_id, v)
                    
            # FIX: Completely rebuild the edge_indices map to match NetworkX's new internal sorting
            node_list = list(G.nodes())
            node_map = {node: i for i, node in enumerate(node_list)}
            edge_indices = [(node_map[u], node_map[v]) for u, v in G.edges()]
            num_edges = len(edge_indices)
                
            new_offsets = np.array([pos[i] for i in node_list])
            for layer in node_layers:
                layer.set_offsets(new_offsets)
                
            edge_segments = np.asarray([(pos[u], pos[v]) for u, v in G.edges()])
            edges.set_segments(edge_segments)

    current_speed = slider_speed.val
    current_power = slider_power.val
    current_decay = slider_decay.val
    current_death = slider_death.val

    final_colors = np.tile(BASE_COLOR, (NUM_NODES, 1))
    final_intensities = np.zeros(NUM_NODES)

    for wave in active_waves[:]:
        new_state = np.copy(wave['state'])

        for u_idx, v_idx in edge_indices:
            if not is_dead[u_idx] and not is_dead[v_idx]:
                if wave['state'][u_idx] > 0.1 and wave['state'][v_idx] == 0.0:
                    if np.random.rand() < current_speed:
                        new_state[v_idx] = max(new_state[v_idx], wave['state'][u_idx] * current_power)
                elif wave['state'][v_idx] > 0.1 and wave['state'][u_idx] == 0.0:
                    if np.random.rand() < current_speed:
                        new_state[u_idx] = max(new_state[u_idx], wave['state'][v_idx] * current_power)

        new_state *= current_decay
        new_state[new_state < SNAP_TO_ZERO] = 0.0
        wave['state'] = np.clip(new_state, 0.0, 1.0)

        for i in range(NUM_NODES):
            if wave['type'] == 'virus' and wave['state'][i] > 0.1 and not is_dead[i]:
                if np.random.rand() < current_death:
                    is_dead[i] = True
                    death_state[i] = 1.0     
                    wave['state'][i] = 0.0   

            if wave['state'][i] > 0:
                final_colors[i] += wave['color'] * wave['state'][i]
                final_intensities[i] = max(final_intensities[i], wave['state'][i])

        if np.max(wave['state']) == 0.0:
            active_waves.remove(wave)

    death_state[is_dead] *= current_decay
    death_state[death_state < 0.01] = 0.0

    flash_state *= current_decay
    flash_state[flash_state < 0.01] = 0.0

    final_colors = np.clip(final_colors, 0.0, 1.0)
    
    for i, layer in enumerate(node_layers):
        factor = i / (GRADIENT_LAYERS - 1)
        layer_colors = BASE_COLOR + (final_colors - BASE_COLOR) * factor
        
        for j in range(NUM_NODES):
            if flash_state[j] > 0:
                flash_blend = BASE_COLOR + (FLASH_COLOR - BASE_COLOR) * flash_state[j]
                layer_colors[j] = flash_blend
            elif is_dead[j]:
                fade_color = BG_COLOR_RGB + (DEAD_COLOR - BG_COLOR_RGB) * death_state[j]
                layer_colors[j] = fade_color
                
        layer.set_facecolor(np.clip(layer_colors, 0.0, 1.0))
        
    edge_rgba = np.zeros((num_edges, 4))
    for i, (u_idx, v_idx) in enumerate(edge_indices):
        avg_rgb = (final_colors[u_idx] + final_colors[v_idx]) / 2.0
        max_intensity = max(final_intensities[u_idx], final_intensities[v_idx])
        alpha = EDGE_ALPHA_BASE + (EDGE_ALPHA_ACTIVE - EDGE_ALPHA_BASE) * max_intensity
        
        if is_dead[u_idx] or is_dead[v_idx]:
            fade_factor = 1.0
            if is_dead[u_idx]: fade_factor = min(fade_factor, death_state[u_idx])
            if is_dead[v_idx]: fade_factor = min(fade_factor, death_state[v_idx])
            alpha *= fade_factor
            avg_rgb = DEAD_COLOR 
        
        edge_rgba[i, :3] = avg_rgb
        edge_rgba[i, 3] = alpha
        
    edges.set_color(np.clip(edge_rgba, 0.0, 1.0))
    
    return tuple(node_layers) + (edges,)

ani = animation.FuncAnimation(fig, update, interval=ANIMATION_INTERVAL, blit=True, cache_frame_data=False)

plt.show()