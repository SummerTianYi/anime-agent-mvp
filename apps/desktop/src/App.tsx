import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

type ConnectionStatus = "connecting" | "online" | "offline";
type AgentState = "idle" | "thinking" | "speaking" | "working" | "error";
type MessageRole = "assistant" | "user";

type ChatMessage = {
  id: string;
  role: MessageRole;
  text: string;
  time: string;
};

type CoreEvent = {
  type: string;
  text?: string;
  message?: string;
  state?: AgentState;
  status?: string;
};

const CORE_URL = import.meta.env.VITE_AGENT_CORE_WS_URL ?? "ws://127.0.0.1:8765/ws";

const stateCopy: Record<AgentState, { label: string; detail: string }> = {
  idle: { label: "待机中", detail: "安静地陪着你" },
  thinking: { label: "思考中", detail: "正在整理你的话" },
  speaking: { label: "回应中", detail: "马上就好" },
  working: { label: "工作中", detail: "任务进行中" },
  error: { label: "需要注意", detail: "连接出现了问题" },
};

const quickPrompts = ["今天适合做什么？", "陪我专注 25 分钟", "给我一句鼓励"];

const initialMessages: ChatMessage[] = [
  {
    id: "welcome",
    role: "assistant",
    text: "晚上好。我是你的本地陪伴 Agent。先从一句简单的聊天开始吧。",
    time: "刚刚",
  },
];

function messageTime() {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

function messageId() {
  return typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function App() {
  const [connection, setConnection] = useState<ConnectionStatus>("connecting");
  const [agentState, setAgentState] = useState<AgentState>("idle");
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [draft, setDraft] = useState("");
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let disposed = false;
    let retryTimer: number | undefined;

    const connect = () => {
      if (disposed) return;

      setConnection("connecting");
      const socket = new WebSocket(CORE_URL);
      socketRef.current = socket;

      socket.onopen = () => {
        socket.send(JSON.stringify({ type: "client.hello", role: "ui" }));
        if (!disposed) setConnection("online");
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as CoreEvent;

          if (payload.type === "core.status") {
            setConnection(payload.status === "online" ? "online" : "offline");
          }

          if (payload.type === "agent.state" && payload.state) {
            setAgentState(payload.state);
          }

          if (payload.type === "chat.response") {
            const response = payload.text ?? payload.message;
            if (response) {
              setMessages((current) => [
                ...current,
                {
                  id: messageId(),
                  role: "assistant",
                  text: response,
                  time: messageTime(),
                },
              ]);
            }
          }
        } catch {
          setAgentState("error");
        }
      };

      socket.onerror = () => socket.close();
      socket.onclose = () => {
        if (disposed) return;
        setConnection("offline");
        setAgentState("idle");
        retryTimer = window.setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      socketRef.current?.close();
    };
  }, []);

  const connectionCopy = useMemo(() => {
    if (connection === "online") return "Core 在线";
    if (connection === "connecting") return "正在连接";
    return "Core 离线";
  }, [connection]);

  const sendMessage = (value: string) => {
    const text = value.trim();
    if (!text) return;

    setMessages((current) => [
      ...current,
      { id: messageId(), role: "user", text, time: messageTime() },
    ]);
    setDraft("");

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({ type: "chat.message", text, messageId: messageId() }),
      );
      return;
    }

    setMessages((current) => [
      ...current,
      {
        id: messageId(),
        role: "assistant",
        text: "本地 Core 还没有上线。请先启动 Agent Core，我会自动重新连接。",
        time: messageTime(),
      },
    ]);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    sendMessage(draft);
  };

  const currentState = stateCopy[agentState];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
          </div>
          <div>
            <p className="brand-name">ANIME AGENT</p>
            <p className="brand-subtitle">LOCAL COMPANION / MVP 01</p>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="local-badge"><i />本地原型</span>
          <span className="version-label">0.1.0</span>
        </div>
      </header>

      <main className="workspace">
        <section className="panel chat-panel">
          <div className="panel-heading chat-heading">
            <div>
              <p className="eyebrow">CONVERSATION</p>
              <h1>和我说点什么</h1>
            </div>
            <div className={`connection-chip ${connection}`}>
              <span className="connection-dot" />
              {connectionCopy}
            </div>
          </div>

          <div className="message-list" aria-live="polite">
            {messages.map((message) => (
              <article className={`message-row ${message.role}`} key={message.id}>
                {message.role === "assistant" && (
                  <div className="message-avatar">A</div>
                )}
                <div className="message-content">
                  <div className="message-meta">
                    <span>{message.role === "assistant" ? "Anime Agent" : "你"}</span>
                    <time>{message.time}</time>
                  </div>
                  <div className="message-bubble">{message.text}</div>
                </div>
              </article>
            ))}
          </div>

          <div className="composer-area">
            <div className="quick-prompts" aria-label="快捷提问">
              {quickPrompts.map((prompt) => (
                <button key={prompt} type="button" onClick={() => sendMessage(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
            <form className="composer" onSubmit={handleSubmit}>
              <input
                aria-label="聊天消息"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="输入消息，按 Enter 发送"
              />
              <button className="send-button" type="submit" aria-label="发送消息">
                <span>发送</span>
                <strong>↗</strong>
              </button>
            </form>
            <p className="composer-note">主体验由桌面 3D 角色承载；当前优先接入 GLM 5.3 Flash。</p>
          </div>
        </section>

        <aside className="panel companion-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">COMPANION STATUS</p>
              <h2>你的桌面伙伴</h2>
            </div>
            <span className="signal-icon" aria-label={connectionCopy}>
              <i />
              <i />
              <i />
            </span>
          </div>

          <div className={`avatar-stage avatar-state-${agentState}`}>
            <div className="avatar-halo" />
            <div className="avatar-spark spark-one">✦</div>
            <div className="avatar-spark spark-two">·</div>
            <div className="avatar-spark spark-three">✦</div>
            <div className="avatar-art" aria-label="占位角色形象">
              <div className="avatar-hair">
                <span className="hair-lock left" />
                <span className="hair-lock right" />
              </div>
              <div className="avatar-face">
                <span className="eye left" />
                <span className="eye right" />
                <span className="blush left" />
                <span className="blush right" />
                <span className="avatar-mouth" />
              </div>
              <div className="avatar-collar" />
              <div className="avatar-ribbon" />
            </div>
          </div>

          <div className="state-summary">
            <div className="state-label-row">
              <span className={`state-dot ${agentState}`} />
              <strong>{currentState.label}</strong>
              <span className="state-live">LIVE</span>
            </div>
            <p>{currentState.detail}</p>
          </div>

          <div className="status-divider" />

          <div className="status-list">
            <div className="status-item">
              <span className="status-icon core-icon">⌁</span>
              <div><small>AGENT CORE</small><strong>{connection === "online" ? "WebSocket 已连接" : "等待本地服务"}</strong></div>
              <span className={`status-mark ${connection === "online" ? "ok" : "pending"}`} />
            </div>
            <div className="status-item">
              <span className="status-icon memory-icon">◒</span>
              <div><small>MEMORY</small><strong>SQLite / 待接入</strong></div>
              <span className="status-mark pending" />
            </div>
            <div className="status-item">
              <span className="status-icon event-icon">◌</span>
              <div><small>EVENT ENGINE</small><strong>Startup / Idle / 规划中</strong></div>
              <span className="status-mark pending" />
            </div>
          </div>

          <div className="companion-footer">
            <span className="footer-line" />
            <span>127.0.0.1 : 8765</span>
          </div>
        </aside>
      </main>

      <footer className="app-footer">
        <span>DESIGNED FOR A QUIET DESKTOP</span>
        <span className="footer-status"><i />本地优先 · 不打扰</span>
      </footer>
    </div>
  );
}

export default App;
