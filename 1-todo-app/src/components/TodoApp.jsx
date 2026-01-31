
import React, { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, ListTodo } from 'lucide-react';
import TodoForm from '@/components/TodoForm';
import TodoItem from '@/components/TodoItem';
import { useToast } from '@/components/ui/use-toast';

const TodoApp = () => {
  const [todos, setTodos] = useState([]);
  const { toast } = useToast();

  // Load todos from localStorage on mount
  useEffect(() => {
    const savedTodos = localStorage.getItem('todos');
    if (savedTodos) {
      try {
        setTodos(JSON.parse(savedTodos));
      } catch (error) {
        console.error('Error loading todos:', error);
      }
    }
  }, []);

  // Save todos to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('todos', JSON.stringify(todos));
  }, [todos]);

  const addTodo = (text) => {
    const newTodo = {
      id: Date.now(),
      text,
      completed: false,
    };
    setTodos([newTodo, ...todos]);
    toast({
      title: "Todo added!",
      description: "Your new task has been added to the list.",
    });
  };

  const deleteTodo = (id) => {
    setTodos(todos.filter((todo) => todo.id !== id));
  };

  const toggleComplete = (id) => {
    setTodos(
      todos.map((todo) =>
        todo.id === id ? { ...todo, completed: !todo.completed } : todo
      )
    );
  };

  const editTodo = (id, newText) => {
    setTodos(
      todos.map((todo) =>
        todo.id === id ? { ...todo, text: newText } : todo
      )
    );
  };

  const completedCount = todos.filter((todo) => todo.completed).length;
  const activeCount = todos.length - completedCount;

  return (
    <>
      <Helmet>
        <title>Todo App - Manage Your Tasks</title>
        <meta
          name="description"
          content="A beautiful and intuitive todo list application to help you organize and manage your daily tasks efficiently."
        />
      </Helmet>

      <div
        className="min-h-screen py-8 px-4 sm:px-6 lg:px-8"
        style={{
          background: `linear-gradient(135deg, #fee2e2 0%, #fecaca 25%, #fca5a5 50%, #f87171 75%, #ef4444 100%)`
        }}
      >
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center mb-8"
          >
            <div className="flex items-center justify-center gap-3 mb-2">
              <CheckCircle2 size={48} className="text-red-800" />
              <h1 className="text-5xl font-bold text-red-900">Todo App</h1>
            </div>
            <p className="text-red-800 text-lg">Organize your tasks, achieve your goals</p>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="bg-white rounded-xl shadow-lg p-4 mb-6"
          >
            <div className="flex justify-around text-center">
              <div>
                <p className="text-3xl font-bold text-red-600">{todos.length}</p>
                <p className="text-sm text-gray-600">Total Tasks</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-orange-600">{activeCount}</p>
                <p className="text-sm text-gray-600">Active</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-green-600">{completedCount}</p>
                <p className="text-sm text-gray-600">Completed</p>
              </div>
            </div>
          </motion.div>

          {/* Todo Form */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="bg-white rounded-xl shadow-lg p-6 mb-6"
          >
            <TodoForm onAddTodo={addTodo} />
          </motion.div>

          {/* Todo List */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="space-y-3"
          >
            <AnimatePresence mode="popLayout">
              {todos.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="bg-white rounded-xl shadow-lg p-12 text-center"
                >
                  <ListTodo size={64} className="mx-auto mb-4 text-red-300" />
                  <h3 className="text-2xl font-semibold text-gray-800 mb-2">
                    No todos yet!
                  </h3>
                  <p className="text-gray-600">
                    Add your first task above to get started.
                  </p>
                </motion.div>
              ) : (
                todos.map((todo) => (
                  <TodoItem
                    key={todo.id}
                    todo={todo}
                    onToggle={toggleComplete}
                    onDelete={deleteTodo}
                    onEdit={editTodo}
                  />
                ))
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      </div>
    </>
  );
};

export default TodoApp;
