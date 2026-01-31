
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, Edit2, Trash2, Save } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

const TodoItem = ({ todo, onToggle, onDelete, onEdit }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(todo.text);
  const { toast } = useToast();

  const handleEdit = () => {
    const trimmedText = editText.trim();
    if (trimmedText && trimmedText !== todo.text) {
      onEdit(todo.id, trimmedText);
      setIsEditing(false);
      toast({
        title: "Todo updated!",
        description: "Your changes have been saved.",
      });
    } else if (!trimmedText) {
      setEditText(todo.text);
      setIsEditing(false);
    } else {
      setIsEditing(false);
    }
  };

  const handleDelete = () => {
    onDelete(todo.id);
    toast({
      title: "Todo deleted",
      description: "The todo has been removed from your list.",
    });
  };

  const handleToggle = () => {
    onToggle(todo.id);
    toast({
      title: todo.completed ? "Todo uncompleted" : "Todo completed!",
      description: todo.completed ? "Keep up the good work!" : "Great job! ✨",
    });
  };

  const handleCancelEdit = () => {
    setEditText(todo.text);
    setIsEditing(false);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -100 }}
      transition={{ duration: 0.2 }}
      className={`bg-white rounded-lg shadow-md hover:shadow-lg transition-all duration-200 p-4 ${
        todo.completed ? 'border-l-4 border-green-500' : 'border-l-4 border-red-500'
      }`}
    >
      <div className="flex items-center gap-3">
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={handleToggle}
          className={`flex-shrink-0 w-6 h-6 rounded border-2 flex items-center justify-center transition-all duration-200 ${
            todo.completed
              ? 'bg-green-500 border-green-500'
              : 'border-red-400 hover:border-red-500'
          }`}
        >
          <AnimatePresence>
            {todo.completed && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
              >
                <Check size={14} className="text-white" />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.button>

        {isEditing ? (
          <input
            type="text"
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleEdit();
              if (e.key === 'Escape') handleCancelEdit();
            }}
            autoFocus
            className="flex-1 px-3 py-1.5 bg-red-50 text-gray-900 rounded border-2 border-red-300 focus:border-red-500 focus:outline-none transition-all duration-200"
          />
        ) : (
          <span
            className={`flex-1 text-gray-800 transition-all duration-200 ${
              todo.completed ? 'line-through text-gray-500' : ''
            }`}
          >
            {todo.text}
          </span>
        )}

        <div className="flex gap-2">
          {isEditing ? (
            <>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={handleEdit}
                className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-all duration-200"
              >
                <Save size={18} />
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={handleCancelEdit}
                className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-all duration-200"
              >
                <X size={18} />
              </motion.button>
            </>
          ) : (
            <>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setIsEditing(true)}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-all duration-200"
              >
                <Edit2 size={18} />
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={handleDelete}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-all duration-200"
              >
                <Trash2 size={18} />
              </motion.button>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default TodoItem;
