import pygame

class MonopolyView:
    def __init__(self, width=1400, height=800):
        self._active_buttons = {}
        self._game_state = None
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Monopoly")
        self.clock = pygame.time.Clock()

        try:
            self.board_img = pygame.image.load("/Users/daniele/PycharmProjects/DS-monopoly-clone/dmonopoly/assets/board.png").convert()
            self.board_img = pygame.transform.smoothscale(self.board_img, (800, 800))
        except FileNotFoundError:
            print("ATTENZIONE: tabellone.png non trovato. Uso uno sfondo nero temporaneo.")
            self.board_image = pygame.Surface((800, 800))
            self.board_image.fill((50, 50, 50))



        self.COLORS = {
            "bg_ui": (40, 44, 52),  # Grigio scuro per il pannello laterale
            "text": (220, 220, 220),  # Bianco sporco per i testi
            "log_bg": (30, 33, 39),  # Sfondo per il box dei messaggi
            "players": [  # Colori per le pedine dei 4 giocatori
                (229, 57, 53),  # Rosso
                (30, 136, 229),  # Blu
                (67, 160, 71),  # Verde
                (253, 216, 53)  # Giallo
            ]
        }

        # Calcolo dell'area UI a destra
        self.ui_x = 800
        self.ui_width = width - 800

        # Font per i testi
        self.font_title = pygame.font.Font(None, 32)
        self.font_text = pygame.font.Font(None, 24)
        self.font_log = pygame.font.Font(None, 22)
        self.font = pygame.font.Font(None, 36)

    def set_game_state(self, game_state: dict):
        self._game_state = game_state

    def render(self, nickname: str):
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.board_img, (0, 0))
        if self._game_state:
            if self._game_state['status'] == 'SERVER_DOWN':
                self._render_reconnecting()
            else:
                self._render_houses()
                self._render_pawns()
                self._render_player_info()
                self._render_messages()
                self._render_buttons(nickname)
        else:
            self._render_loading()

        pygame.display.flip()
        self.clock.tick(30)

    def _render_houses(self):
        """Disegna le casette leggendo direttamente da self._game_state."""
        # 1. Recupera il dizionario della board e poi la lista degli spazi
        board_data = self._game_state.get("board", {})
        spaces_list = board_data.get("spaces", [])

        # 2. Usa enumerate per avere l'indice (idx) e i dati della casella (space)
        for idx, space in enumerate(spaces_list):
            houses = space.get("houses", 0)

            if houses > 0:
                x, y = self._get_space_position(idx)

                for i in range(houses):
                    rect = pygame.Rect(x - 20 + (i * 12), y - 30, 10, 10)
                    pygame.draw.rect(self.screen, (0, 255, 0), rect)

    def _render_pawns(self):
        """Disegna le pedine dei giocatori usando cerchi colorati."""
        players = self._game_state.get("players", [])
        for i, player in enumerate(players):
            pos = player.get("position", 0)
            x, y = self._get_space_position(pos)

            # Applichiamo un minuscolo offset se più pedine sono sulla stessa casella
            offset_x = (i % 2) * 4 - 2
            offset_y = (i // 2) * 4 - 2

            color = self.COLORS["players"][i % len(self.COLORS["players"])]
            pygame.draw.circle(self.screen, color, (x + offset_x, y + offset_y), 12)
            # Bordino nero per renderle più visibili
            pygame.draw.circle(self.screen, (0, 0, 0), (x + offset_x, y + offset_y), 12, 2)

    def _get_space_position(self, space_idx: int):
        start_x, start_y = (750, 750)
        spacing = 70
        if space_idx <= 10:
            new_x = start_x - spacing * space_idx
            new_y = start_y
        elif 10 < space_idx <= 20:
            new_x = start_x - spacing * 10
            new_y = start_y - spacing * (space_idx - 10)
        elif 20 < space_idx <= 30:
            new_x = start_x - spacing * -(space_idx - 30)
            new_y = start_y - spacing * 10
        else:
            new_x = start_x
            new_y = start_y - spacing * -(space_idx - 40)
        return new_x, new_y

    def _render_player_info(self):
        """Disegna il pannello di destra con i bilanci e il turno attuale."""
        title = self.font_title.render("GIOCATORI", True, self.COLORS["text"])
        self.screen.blit(title, (self.ui_x + 20, 20))

        current_turn = self._game_state.get("current_turn_nickname")
        players = self._game_state.get("players", [])

        y_offset = 80
        for i, player in enumerate(players):
            name = player.get("nickname", "Sconosciuto")
            balance = player.get("balance", 0)

            # Se è il turno di questo giocatore, evidenzia il testo o aggiungi un asterisco
            prefix = "▶ " if current_turn == name else "  "

            # Disegna un quadratino col colore del giocatore
            color = self.COLORS["players"][i % len(self.COLORS["players"])]
            pygame.draw.rect(self.screen, color, (self.ui_x + 20, y_offset, 15, 15))

            # Disegna i dati
            info_text = self.font_text.render(f"{prefix}{name}: €{balance}", True, self.COLORS["text"])
            self.screen.blit(info_text, (self.ui_x + 45, y_offset - 2))

            y_offset += 40

    def _render_messages(self):
        """Disegna il box testuale in basso a destra con gli ultimi eventi."""
        msg = self._game_state.get("last_event", "")
        if not msg:
            return

        # Crea un rettangolo per contenere il log in basso a destra
        box_rect = pygame.Rect(self.ui_x + 20, 600, self.ui_width - 40, 150)
        pygame.draw.rect(self.screen, self.COLORS["log_bg"], box_rect, border_radius=8)

        # Testo
        title = self.font_text.render("Ultimo Evento:", True, (150, 150, 150))
        self.screen.blit(title, (box_rect.x + 10, box_rect.y + 10))

        # Permette al testo di non uscire dai bordi (wrapping base)
        words = msg.split()
        lines = []
        current_line = ""
        for word in words:
            if self.font_log.size(current_line + word)[0] < box_rect.width - 20:
                current_line += word + " "
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line)

        # Stampa le linee splittate
        y_text = box_rect.y + 40
        for line in lines:
            line_surf = self.font_log.render(line, True, self.COLORS["text"])
            self.screen.blit(line_surf, (box_rect.x + 10, y_text))
            y_text += 25

    def _render_loading(self):
        text = self.font_title.render("Loading", True, self.COLORS["text"])
        self.screen.blit(text, (self.ui_x + 20, 400))

    def _render_buttons(self, nickname: str):
        """Disegna i bottoni solo se è il mio turno e in base alle azioni permesse."""
        self._active_buttons.clear()

        current_turn_player = self._game_state.get("current_turn_nickname")
        allowed_actions = self._game_state.get("allowed_actions", [])

        start_x = 800
        start_y = 530
        btn_width = 120
        btn_height = 50
        spacing = 10

        if self._game_state['status'] == 'LOBBY':
            rect = pygame.Rect(start_x, start_y, btn_width, btn_height)
            pygame.draw.rect(self.screen, (50, 200, 50), rect)
            text_surf = self.font.render("ready", True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)
            self._active_buttons["ready"] = rect
            return

        if current_turn_player != nickname:
            return

        # Disegna un bottone per ogni azione permessa
        for i, action_name in enumerate(allowed_actions):
            x = start_x + (i * (btn_width + spacing))
            y = start_y
            rect = pygame.Rect(x, y, btn_width, btn_height)
            pygame.draw.rect(self.screen, (50, 200, 50), rect)
            text_surf = self.font.render(action_name, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)
            self._active_buttons[action_name] = rect

    def get_button(self, pos: tuple[int, int]):
        """Restituisce il nome dell'azione se il click cade dentro un bottone attivo."""
        for action_name, rect in self._active_buttons.items():
            if rect.collidepoint(pos):
                return action_name
        return None

    def get_game_state(self):
        return self._game_state

    def _render_reconnecting(self):
        text = self.font_title.render("SERVER DOWN! TRYING TO RECONNECT...", True, self.COLORS["text"])
        self.screen.blit(text, (self.ui_x + 20, 400))