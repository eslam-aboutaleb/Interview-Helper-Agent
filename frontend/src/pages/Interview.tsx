import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMutation } from '@tanstack/react-query';
import {
  Send,
  Bot,
  User,
  Play,
  RotateCcw,
  Sparkles,
  Target,
  BarChart3,
  BookOpen,
  MessageSquare,
} from 'lucide-react';
import { interviewsApi } from '../services/api';
import {
  InterviewSession,
  InterviewSessionCreate,
  InterviewEvaluation,
  InterviewTurnResponse,
} from '../types';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { EvaluationCard } from '../components/EvaluationCard';
import toast from 'react-hot-toast';

interface ChatMessage {
  id: string;
  role: 'interviewer' | 'candidate';
  content: string;
  evaluation?: InterviewEvaluation;
}

const SESSION_TYPE_OPTIONS = [
  { value: 'mixed', label: 'Mixed (Technical & Behavioral)' },
  { value: 'technical', label: 'Technical Only' },
  { value: 'behavioral', label: 'Behavioral Only' },
];

const DIFFICULTY_OPTIONS = [1, 2, 3, 4, 5].map((d) => ({
  value: String(d),
  label: `Level ${d}`,
}));

const MAX_TURNS_OPTIONS = [3, 5, 7, 10, 15].map((t) => ({
  value: String(t),
  label: `${t} questions`,
}));

const Interview: React.FC = () => {
  const [phase, setPhase] = useState<'setup' | 'active' | 'completed'>('setup');
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [modelAnswer, setModelAnswer] = useState<string | null>(null);

  // Setup form state
  const [jobTitle, setJobTitle] = useState('');
  const [sessionType, setSessionType] = useState('mixed');
  const [difficulty, setDifficulty] = useState('3');
  const [maxTurns, setMaxTurns] = useState('7');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to the latest message.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, modelAnswer]);

  // Focus the answer input when a new interviewer question arrives.
  useEffect(() => {
    if (phase === 'active') {
      inputRef.current?.focus();
    }
  }, [chatMessages, phase]);

  const startMutation = useMutation({
    mutationFn: (data: InterviewSessionCreate) => interviewsApi.start(data).then((r) => r.data),
    onSuccess: async (newSession) => {
      setSession(newSession);
      setPhase('active');
      setSummary(null);
      setModelAnswer(null);
      try {
        const msgs = await interviewsApi.getMessages(newSession.id).then((r) => r.data);
        setChatMessages(
          msgs
            .filter((m) => m.role !== 'system')
            .map((m) => ({
              id: String(m.id),
              role: m.role === 'candidate' ? 'candidate' : 'interviewer',
              content: m.content,
            }))
        );
      } catch {
        toast.error('Failed to load the first question');
      }
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || 'Failed to start interview');
    },
  });

  const submitMutation = useMutation({
    mutationFn: ({ sessionId, answer }: { sessionId: number; answer: string }) =>
      interviewsApi.submitAnswer(sessionId, { answer }).then((r) => r.data),
    onSuccess: (turn: InterviewTurnResponse) => {
      setModelAnswer(null);
      setChatMessages((prev) => {
        const updated = [...prev];
        const lastIdx = updated.map((m) => m.role).lastIndexOf('candidate');
        if (lastIdx !== -1) {
          updated[lastIdx] = { ...updated[lastIdx], evaluation: turn.evaluation };
        }
        if (!turn.completed && turn.next_question) {
          updated.push({
            id: `interviewer-${Date.now()}`,
            role: 'interviewer',
            content: turn.next_question,
          });
        }
        return updated;
      });
      if (turn.completed) {
        setSummary(turn.summary);
        setPhase('completed');
      }
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || 'Failed to submit answer');
    },
  });

  const modelAnswerMutation = useMutation({
    mutationFn: (question: string) => interviewsApi.modelAnswer({ question }).then((r) => r.data),
    onSuccess: (data) => {
      setModelAnswer(data.model_answer);
    },
    onError: () => {
      toast.error('Failed to generate model answer');
    },
  });

  const handleStart = (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobTitle.trim()) {
      toast.error('Please enter a job title');
      return;
    }
    startMutation.mutate({
      job_title: jobTitle.trim(),
      session_type: sessionType as InterviewSessionCreate['session_type'],
      difficulty: parseInt(difficulty, 10),
      max_turns: parseInt(maxTurns, 10),
    });
  };

  const handleSubmitAnswer = (e: React.FormEvent) => {
    e.preventDefault();
    const answer = input.trim();
    if (!answer || !session || submitMutation.isPending) return;

    const candidateMsg: ChatMessage = {
      id: `candidate-${Date.now()}`,
      role: 'candidate',
      content: answer,
    };
    setChatMessages((prev) => [...prev, candidateMsg]);
    setInput('');

    submitMutation.mutate({ sessionId: session.id, answer });
  };

  const handleReset = () => {
    setPhase('setup');
    setSession(null);
    setChatMessages([]);
    setSummary(null);
    setModelAnswer(null);
    setInput('');
  };

  const lastInterviewerQuestion = [...chatMessages]
    .reverse()
    .find((m) => m.role === 'interviewer')?.content;

  /* ------------------------------ Setup phase ------------------------------ */
  if (phase === 'setup') {
    return (
      <div className="max-w-2xl mx-auto">
        <motion.div
          className="text-center mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl shadow-strong mb-4">
            <MessageSquare className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-slate-900">Mock Interview</h1>
          <p className="text-lg text-slate-600 mt-2 max-w-xl mx-auto">
            Practice with an AI interviewer that adapts to your answers, scores each response, and
            guides you to the next question.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <Card>
            <CardContent className="p-6">
              <form onSubmit={handleStart} className="space-y-5">
                <Input
                  label="Job Title"
                  placeholder="e.g., Senior Frontend Engineer"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  required
                />
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <Select
                    label="Session Type"
                    value={sessionType}
                    onChange={(e) => setSessionType(e.target.value)}
                    options={SESSION_TYPE_OPTIONS}
                  />
                  <Select
                    label="Difficulty"
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                    options={DIFFICULTY_OPTIONS}
                  />
                  <Select
                    label="Length"
                    value={maxTurns}
                    onChange={(e) => setMaxTurns(e.target.value)}
                    options={MAX_TURNS_OPTIONS}
                  />
                </div>
                <Button
                  type="submit"
                  size="lg"
                  className="w-full"
                  isLoading={startMutation.isPending}
                >
                  <Play className="w-5 h-5" />
                  Start Interview
                </Button>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  /* ---------------------------- Completed phase ---------------------------- */
  if (phase === 'completed') {
    const avg = (summary?.overall_average as number) ?? 0;
    const turns = (summary?.turns as number) ?? 0;
    const strengths = (summary?.strengths as string[]) ?? [];
    const gaps = (summary?.gaps as string[]) ?? [];
    const finalDifficulty = (summary?.final_difficulty as number) ?? session?.difficulty ?? 3;

    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl shadow-strong mb-4">
            <BarChart3 className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900">Interview Complete</h1>
          <p className="text-slate-600 mt-1">
            {session?.job_title} · {turns} questions answered
          </p>
        </motion.div>

        <Card>
          <CardContent className="p-6 space-y-6">
            <div className="text-center">
              <div className="text-5xl font-bold text-slate-900">{avg.toFixed(1)}</div>
              <div className="text-sm text-slate-500 mt-1">Average score / 10</div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-50 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-slate-900">{turns}</div>
                <div className="text-xs text-slate-500">Questions</div>
              </div>
              <div className="bg-slate-50 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-slate-900">Level {finalDifficulty}</div>
                <div className="text-xs text-slate-500">Final difficulty</div>
              </div>
            </div>

            {strengths.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-4 h-4 text-green-600" />
                  <span className="text-sm font-semibold text-green-700">Your strengths</span>
                </div>
                <ul className="space-y-1">
                  {strengths.map((s, i) => (
                    <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                      <span className="text-green-500 mt-1">•</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {gaps.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-4 h-4 text-amber-600" />
                  <span className="text-sm font-semibold text-amber-700">Focus areas</span>
                </div>
                <ul className="space-y-1">
                  {gaps.map((g, i) => (
                    <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                      <span className="text-amber-500 mt-1">•</span>
                      <span>{g}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <Button onClick={handleReset} size="lg" className="w-full">
              <RotateCcw className="w-5 h-5" />
              Start New Interview
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  /* ----------------------------- Active phase ------------------------------ */
  return (
    <div className="max-w-4xl mx-auto flex flex-col h-[calc(100vh-10rem)]">
      {/* Session header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{session?.job_title}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="primary">{session?.session_type}</Badge>
            <Badge variant="neutral">Level {session?.difficulty}</Badge>
            <Badge variant="neutral">
              Question {(session?.current_turn ?? 0) + 1} of {session?.max_turns}
            </Badge>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={handleReset}>
          <RotateCcw className="w-4 h-4" />
          End
        </Button>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden mb-4">
        <motion.div
          className="h-full bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full"
          initial={{ width: 0 }}
          animate={{
            width: `${((session?.current_turn ?? 0) / (session?.max_turns ?? 1)) * 100}%`,
          }}
          transition={{ duration: 0.5 }}
        />
      </div>

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-2 pb-4">
        <AnimatePresence initial={false}>
          {chatMessages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex gap-3 ${msg.role === 'candidate' ? 'flex-row-reverse' : ''}`}
            >
              <div
                className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                  msg.role === 'interviewer'
                    ? 'bg-gradient-to-br from-indigo-500 to-purple-600'
                    : 'bg-slate-700'
                }`}
              >
                {msg.role === 'interviewer' ? (
                  <Bot className="w-4 h-4 text-white" />
                ) : (
                  <User className="w-4 h-4 text-white" />
                )}
              </div>
              <div
                className={`max-w-[80%] ${msg.role === 'candidate' ? 'text-right' : 'text-left'}`}
              >
                <div
                  className={`inline-block rounded-2xl px-4 py-3 text-left text-sm leading-relaxed shadow-soft ${
                    msg.role === 'interviewer'
                      ? 'bg-white border border-slate-200 text-slate-900 rounded-tl-sm'
                      : 'bg-gradient-to-br from-indigo-600 to-purple-600 text-white rounded-tr-sm'
                  }`}
                >
                  {msg.content}
                </div>
                {msg.evaluation && (
                  <div className="mt-2 max-w-md">
                    <EvaluationCard evaluation={msg.evaluation} />
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Model answer panel */}
        <AnimatePresence>
          {modelAnswer && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex gap-3"
            >
              <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-br from-amber-400 to-orange-500">
                <BookOpen className="w-4 h-4 text-white" />
              </div>
              <div className="max-w-[80%]">
                <div className="inline-block rounded-2xl rounded-tl-sm px-4 py-3 text-left text-sm leading-relaxed bg-amber-50 border border-amber-200 text-amber-900 shadow-soft">
                  <div className="font-semibold mb-1 flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    Model Answer
                  </div>
                  <div className="whitespace-pre-wrap">{modelAnswer}</div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {submitMutation.isPending && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-soft">
              <Skeleton width={180} height={14} />
              <Skeleton width={120} height={14} className="mt-2" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Model answer trigger */}
      {lastInterviewerQuestion && !modelAnswer && !submitMutation.isPending && (
        <div className="mb-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => modelAnswerMutation.mutate(lastInterviewerQuestion)}
            disabled={modelAnswerMutation.isPending}
            isLoading={modelAnswerMutation.isPending}
          >
            <BookOpen className="w-4 h-4" />
            Show model answer
          </Button>
        </div>
      )}

      {/* Answer input */}
      <form onSubmit={handleSubmitAnswer} className="flex gap-3">
        <Input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your answer..."
          disabled={submitMutation.isPending}
          className="flex-1"
          aria-label="Your answer"
        />
        <Button type="submit" disabled={!input.trim() || submitMutation.isPending}>
          <Send className="w-4 h-4" />
          <span className="hidden sm:inline">Send</span>
        </Button>
      </form>
    </div>
  );
};

export default Interview;
