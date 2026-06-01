import random
import json
import threading

class GameState:
    #Gamestates
    def __init__(self):
        self.players={}
        self.current_word=None
        self.current_drawer=None
        self.current_guesser=None
        self.scores={}
        self.game_phase="lobby"

#add players to the dict, initialize players
    def add_player(self,nick,client_socket):
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
        self._broadcast({"type": "timer", "seconds": 60})
        self.timer = threading.Timer(60, self._time_up)
        self.timer.start()

    def _time_up(self):
       if self.game_phase == "playing":
           self._broadcast({"type": "time_up", "word": self.current_word})
           self._switch_turns()


