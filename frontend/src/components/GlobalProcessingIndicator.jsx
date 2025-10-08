import React from "react";
import { useProcessing } from "../contexts/ProcessingContext";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Settings } from "lucide-react";
import { useNavigate } from "react-router-dom";

const GlobalProcessingIndicator = () => {
  const {
    activeTasks,
    globalProcessingCount,
    isConnected,
    hasActiveProcessing,
  } = useProcessing();
  const navigate = useNavigate();

  if (!hasActiveProcessing) {
    return null;
  }

  const handleViewTask = (task) => {
    if (task.file_id) {
      navigate(`/files/${task.file_id}/preview`);
    }
  };

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {/* Connection Status */}
      <div className="flex items-center justify-end">
        <Badge
          variant={isConnected ? "default" : "destructive"}
          className="flex items-center text-xs"
        >
          <div
            className={`w-2 h-2 rounded-full mr-1 ${
              isConnected ? "bg-green-400" : "bg-red-400"
            }`}
          />
          {isConnected ? "Connecté" : "Déconnecté"}
        </Badge>
      </div>

      {/* Active Tasks */}
      {activeTasks.map((task) => (
        <div
          key={task.task_id}
          className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 min-w-80"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <Settings className="h-4 w-4 text-blue-500 animate-spin" />
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Traitement en cours
              </span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleViewTask(task)}
              className="text-xs"
            >
              Voir
            </Button>
          </div>

          <div className="space-y-1">
            <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
              {task.filename}
            </p>

            {/* Progress Bar */}
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${task.progress}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>{task.progress}%</span>
              <span>{task.message || "Traitement..."}</span>
            </div>
          </div>
        </div>
      ))}

      {/* Summary Badge */}
      {globalProcessingCount > 1 && (
        <div className="flex justify-end">
          <Badge variant="outline" className="text-xs">
            {globalProcessingCount} tâches actives
          </Badge>
        </div>
      )}
    </div>
  );
};

export default GlobalProcessingIndicator;
