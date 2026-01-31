
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus } from 'lucide-react';

const TodoForm = ({ onAddTodo }) => {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmedValue = inputValue.trim();
    
    if (trimmedValue) {
      onAddTodo(trimmedValue);
      setInputValue('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="What needs to be done?"
          className="flex-1 px-4 py-3 bg-red-50 text-gray-900 placeholder-gray-400 rounded-lg border-2 border-red-200 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-500/20 transition-all duration-200"
        />
        <motion.button
          type="submit"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="px-6 py-3 bg-black hover:bg-gray-800 text-white font-medium rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 flex items-center gap-2"
        >
          <Plus size={20} />
          <span className="hidden sm:inline">Add Todo</span>
        </motion.button>
      </div>
    </form>
  );
};

export default TodoForm;
