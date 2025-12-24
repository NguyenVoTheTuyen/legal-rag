import React, { useState } from 'react';
import { Send, Settings, Search, Globe, ChevronRight, MessageSquare, Scale, Loader2, BookOpen, ExternalLink, Sliders } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChatStore } from './hooks/useChat';

const App: React.FC = () => {
  const { messages, isTyping, sendMessage } = useChatStore();
  const [input, setInput] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [options, setOptions] = useState({
    max_iterations: 3,
    top_k: 3,
    enable_web_search: true,
  });

  const handleSend = () => {
    if (!input.trim() || isTyping) return;
    sendMessage(input, options);
    setInput('');
  };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Sidebar - App Info & Settings Toggle */}
      <div className="w-16 md:w-20 flex flex-col items-center py-6 bg-white dark:bg-slate-900 border-r border-border">
        <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-white mb-8 shadow-lg shadow-primary/20">
          <Scale size={24} />
        </div>
        
        <button 
          onClick={() => setShowSettings(!showSettings)}
          className={`p-3 rounded-xl transition-all ${showSettings ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-secondary'}`}
        >
          <Settings size={24} />
        </button>
        
        <div className="mt-auto flex flex-col items-center gap-6">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" title="Backend Online" />
          <div className="w-10 h-10 rounded-full overflow-hidden border border-border">
            <img src="https://ui-avatars.com/api/?name=Legal+RAG&background=random" alt="User" />
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-6 border-b border-border bg-white/50 dark:bg-slate-900/50 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">Legal RAG Assistant</h1>
            <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-bold uppercase tracking-wider">v1.0.0</span>
          </div>
          
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1.5 grayscale opacity-70">
              <Search size={14} />
              <span>Internal Search</span>
            </div>
            {options.enable_web_search && (
              <div className="flex items-center gap-1.5 text-blue-500 font-medium">
                <Globe size={14} />
                <span>Web Search Enabled</span>
              </div>
            )}
          </div>
        </header>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-2xl mx-auto space-y-6">
              <div className="w-20 h-20 rounded-3xl bg-primary/5 flex items-center justify-center text-primary mb-4">
                <MessageSquare size={40} />
              </div>
              <h2 className="text-3xl font-bold tracking-tight">Chào mừng bạn đến với Legal RAG</h2>
              <p className="text-muted-foreground text-lg leading-relaxed">
                Hệ thống RAG nâng cao kết hợp giữa cơ sở dữ liệu luật pháp nội bộ và tìm kiếm web để cung cấp câu trả lời chính xác, đáng tin cậy.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                {['Quy định về bảo hiểm xã hội 2024?', 'Thủ tục thành lập doanh nghiệp?', 'Luật đất đai có thay đổi gì mới?', 'Cách tính thuế thu nhập cá nhân?'].map((q) => (
                  <button 
                    key={q}
                    onClick={() => { setInput(q); }}
                    className="p-4 rounded-2xl border border-border hover:border-primary hover:bg-primary/5 transition-all text-left text-sm group"
                  >
                    <span className="group-hover:text-primary transition-colors">{q}</span>
                    <ChevronRight size={14} className="float-right text-muted-foreground group-hover:text-primary" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] space-y-2 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                  <div className={`inline-block p-4 rounded-2xl shadow-sm ${
                    msg.role === 'user' 
                      ? 'bg-primary text-white rounded-tr-none' 
                      : 'bg-white dark:bg-slate-800 border border-border rounded-tl-none'
                  }`}>
                    {msg.isLoading ? (
                      <div className="flex items-center gap-3 px-2 py-1">
                        <Loader2 className="animate-spin text-primary" size={20} />
                        <span className="text-muted-foreground text-sm font-medium animate-pulse">Đang nghiên cứu và tổng hợp...</span>
                      </div>
                    ) : (
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        {msg.content}
                      </div>
                    )}
                  </div>
                  
                  {!msg.isLoading && msg.metadata && (
                    <motion.div 
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-4 space-y-4"
                    >
                      {/* Reasoning Summary */}
                      <div className="flex flex-wrap gap-2">
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary border border-border text-[11px] font-bold text-muted-foreground uppercase">
                          <Sliders size={12} /> {msg.metadata.iterations} Iterations
                        </span>
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-[11px] font-bold text-blue-600 uppercase">
                          <Search size={12} /> Query: "{msg.metadata.query_used}"
                        </span>
                      </div>

                      {/* Source Panels */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Legal Sources */}
                        {msg.metadata.search_results && msg.metadata.search_results.length > 0 && (
                          <div className="space-y-2">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                              <BookOpen size={14} /> Nguồn Pháp Lý
                            </h4>
                            <div className="space-y-2">
                              {msg.metadata.search_results.map((res, i) => (
                                <div key={i} className="p-3 bg-white dark:bg-slate-800 border border-border rounded-xl text-xs shadow-sm hover:shadow-md transition-shadow">
                                  <div className="font-bold text-primary mb-1">{res.title}</div>
                                  <p className="text-muted-foreground line-clamp-3 leading-relaxed">{res.content}</p>
                                  <div className="mt-2 flex items-center justify-between opacity-60">
                                    <span>Score: {(res.score * 100).toFixed(1)}%</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Web Results */}
                        {msg.metadata.web_results && msg.metadata.web_results.length > 0 && (
                          <div className="space-y-2">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5 text-blue-600">
                              <Globe size={14} /> Thông Tin Web
                            </h4>
                            <div className="space-y-2">
                              {msg.metadata.web_results.map((res, i) => (
                                <a 
                                  key={i} 
                                  href={res.url} 
                                  target="_blank" 
                                  rel="noreferrer"
                                  className="block p-3 bg-blue-50/30 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30 rounded-xl text-xs shadow-sm hover:bg-blue-50 transition-colors"
                                >
                                  <div className="font-bold text-blue-700 dark:text-blue-400 mb-1 flex items-center justify-between">
                                    {res.title}
                                    <ExternalLink size={12} />
                                  </div>
                                  <p className="text-muted-foreground line-clamp-2">{res.snippet}</p>
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                  
                  <div className="text-[10px] text-muted-foreground px-2">
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))
          )}
          {isTyping && messages.length > 0 && messages[messages.length-1].role === 'user' && (
             <div className="flex justify-start">
               <div className="bg-white dark:bg-slate-800 border border-border p-4 rounded-2xl rounded-tl-none shadow-sm">
                  <div className="flex items-center gap-3 px-2 py-1">
                    <Loader2 className="animate-spin text-primary" size={20} />
                    <span className="text-muted-foreground text-sm font-medium animate-pulse">Hệ thống đang suy nghĩ...</span>
                  </div>
               </div>
             </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-6 border-t border-border bg-white dark:bg-slate-900 shadow-[0_-4px_20px_-5px_rgba(0,0,0,0.05)]">
          <div className="max-w-4xl mx-auto flex items-center gap-4 bg-secondary/50 p-2 rounded-2xl border border-border focus-within:border-primary/50 transition-all">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Đặt câu hỏi về luật pháp Việt Nam..."
              className="flex-1 bg-transparent px-4 py-3 focus:outline-none text-sm"
              disabled={isTyping}
            />
            <button 
              onClick={handleSend}
              disabled={!input.trim() || isTyping}
              className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${
                input.trim() && !isTyping 
                  ? 'bg-primary text-white shadow-lg shadow-primary/20 hover:scale-105 active:scale-95' 
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
              }`}
            >
              <Send size={20} />
            </button>
          </div>
          <p className="text-[10px] text-center mt-4 text-muted-foreground font-medium grayscale opacity-60">
            Hệ thống có thể đưa ra câu hỏi không chính xác. Luôn kiểm tra lại các nguồn pháp lý chính thống.
          </p>
        </div>

        {/* Settings Overlay */}
        <AnimatePresence>
          {showSettings && (
            <>
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setShowSettings(false)}
                className="absolute inset-0 bg-black/20 backdrop-blur-sm z-10"
              />
              <motion.div 
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                className="absolute right-0 top-0 bottom-0 w-80 bg-white dark:bg-slate-900 shadow-2xl z-20 p-8 border-l border-border"
              >
                <div className="flex items-center justify-between mb-8">
                  <h3 className="text-xl font-bold">Cấu hình</h3>
                  <button onClick={() => setShowSettings(false)} className="p-2 hover:bg-secondary rounded-lg transition-colors">
                    <ChevronRight size={20} />
                  </button>
                </div>

                <div className="space-y-8">
                  <div className="space-y-4">
                    <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                      <Globe size={14} /> Web Search
                    </label>
                    <div className="flex items-center justify-between p-4 rounded-2xl border border-border bg-secondary/30">
                      <span className="text-sm font-medium">Tìm kiếm bổ sung</span>
                      <button 
                        onClick={() => setOptions({...options, enable_web_search: !options.enable_web_search})}
                        className={`w-12 h-6 rounded-full transition-all relative ${options.enable_web_search ? 'bg-primary' : 'bg-muted'}`}
                      >
                        <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${options.enable_web_search ? 'left-7' : 'left-1'}`} />
                      </button>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                       Max Iterations: {options.max_iterations}
                    </label>
                    <input 
                      type="range" min="1" max="5" step="1"
                      value={options.max_iterations}
                      onChange={(e) => setOptions({...options, max_iterations: parseInt(e.target.value)})}
                      className="w-full accent-primary"
                    />
                    <p className="text-[10px] text-muted-foreground italic">Số lượt suy luận tối đa để tìm câu trả lời.</p>
                  </div>

                  <div className="space-y-4">
                    <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                       Top K Results: {options.top_k}
                    </label>
                    <input 
                      type="range" min="1" max="10" step="1"
                      value={options.top_k}
                      onChange={(e) => setOptions({...options, top_k: parseInt(e.target.value)})}
                      className="w-full accent-primary"
                    />
                    <p className="text-[10px] text-muted-foreground italic">Số lượng tài liệu luật pháp tối đa được tham chiếu.</p>
                  </div>
                </div>

                <div className="absolute bottom-8 left-8 right-8">
                   <button 
                    onClick={() => {
                        window.confirm('Xoá toàn bộ lịch sử trò chuyện?') && useChatStore().setMessages([]);
                        setShowSettings(false);
                    }}
                    className="w-full py-3 rounded-xl border border-red-200 text-red-500 text-sm font-bold hover:bg-red-50 transition-colors"
                  >
                    Xoá lịch sử
                  </button>
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
};

export default App;
