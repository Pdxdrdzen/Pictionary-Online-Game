import random
import json
import threading

class GameState:
    #Gamestates
    def __init__(self,player_list,socket_map):
        self.players={nick:sock for sock, nick in socket_map.items() if nick in player_list}
        self.current_word=None
        self.current_drawer=None
        self.current_guesser=None
        self.scores={nick: 0 for nick in player_list}
        self.game_phase="lobby"
        self.max_rounds=len(player_list)*2
        self.current_round=0
        self.quick_shot=False
        self.player_order=player_list

    def start(self):
        self._start_game()

        # add players to the dict, initialize players(currently passing)

    def add_player(self,nick,client_socket):
        pass
        self.players[nick]=client_socket
        self.scores[nick]=0
        self._send(nick, {"type": "lobby", "msg": "Waiting for other players..."})
        print(f"Player {nick} has joined the game, player count: {len(self.players)}")
        if len(self.players)==2:
            print("Game started!")
            self._start_game()
    #Setup the game start
    def _start_game(self):
        print("_start_game triggered")
        nicks=list(self.players.keys())#Only nicknames taken
        self.current_drawer=nicks[0]#role - drawer
        self.current_guesser=nicks[1]#role = guesser
        self.game_phase="playing"#change gamephase into play

        with open("../words/words.txt","r",encoding="utf-8") as f:
            words=[line.strip() for line in f]
        self.current_word=random.choice(words)
        #Logic to sending the word only to the drawer
        self._send(self.current_drawer,{"type":"word","word":self.current_word})

        self._send(self.current_drawer,{"type":"role","role":"drawer"})
        self._send(self.current_guesser,{"type":"role","role":"guesser"})
        self._start_timer()

    def handle_message(self,nick,raw_msg):
        msg=json.loads(raw_msg)#refactor the JSON string into Python dict

        if self.game_phase!="playing":
            return
        if msg["type"]=="guess" and nick ==self.current_guesser:#Check if the message type is "guess" sent by the guesser
            if msg["payload"].lower()==self.current_word.lower():
                self.scores[nick]+=1
                self._broadcast({"type":"correct","player":nick})#let everyone now that *nick* guessed correctly
                self._switch_turns()
            else:
                self._send(nick,{"type": "wrong"})#let the guesser know they are wrong
        elif msg["type"]=="draw" and nick==self.current_drawer:#if the message is a draw message sent by the drawer, forward it for the guesser
            self._send(self.current_guesser,msg)

    def _switch_turns(self):
        if self.quick_shot:
            scores = list(self.scores.values())
            if scores[0] != scores[1]:  # ktoś wyszedł na prowadzenie
                self.quick_shot = False
                self._end_game()
                return
        self.current_round+=1
        if self.current_round>=self.max_rounds:
            self._end_game()
            return
        if hasattr(self,'timer'):
            self.timer.cancel()
        self._start_timer()
        self._broadcast({"type":"clear_canvas"})
        self._broadcast({"type":"scores","scores":self.scores})
        self.current_drawer,self.current_guesser=self.current_guesser,self.current_drawer
        with open("../words/words.txt","r",encoding="utf-8") as f:
            words=[line.strip() for line in f]
        self.current_word=random.choice(words)
        self._send(self.current_drawer,{"type":"word","word":self.current_word})
        self._send(self.current_drawer,{"type":"role","role":"drawer"})
        self._send(self.current_guesser,{"type":"role","role":"guesser"})


    def _send(self,nick,message):
        data=json.dumps(message)+ '\n'
        self.players[nick].send(data.encode('utf-8'))#take the socket of one player, then refactor python dict into JSON string using utf-8 encoding

    def _broadcast(self,message):
        data=json.dumps(message)+ '\n'
        for sock in self.players.values(): #iterate through sockets
            sock.send(data.encode('utf-8'))#for every socket found, send the same thing

    def _start_timer(self):
        seconds = 10 if self.quick_shot else 60
        self._broadcast({"type": "timer", "seconds": seconds})
        self.timer = threading.Timer(seconds, self._time_up)
        self.timer.start()

    def _time_up(self):
       if self.game_phase == "playing":
           self._broadcast({"type": "time_up", "word": self.current_word})
           self._switch_turns()

    def _end_game(self):
        if hasattr(self, 'timer'):
            self.timer.cancel()
        scores = list(self.scores.values())
        if scores[0] == scores[1]:  # remis!
            self.game_phase = "playing"
            self.current_round = 0
            self.max_rounds = 999  # nieskończone rundy aż ktoś wygra
            self._broadcast({"type": "quick_shot", "msg": "Remis! Kto pierwszy odgadnie haslo wygrywa! Runda - 10 sekund!"})
            self.quick_shot = True
            self._switch_turns()
        else:
            winner = max(self.scores, key=self.scores.get)
            self._broadcast({"type": "game_over", "winner": winner, "scores": self.scores})
            self.game_phase = "lobby"


