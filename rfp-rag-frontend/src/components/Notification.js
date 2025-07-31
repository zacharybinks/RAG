/*
-------------------------------------------------------------------
File: src/components/Notification.js (Complete)
Description: The UI component for the notification message.
-------------------------------------------------------------------
*/
import React from 'react';
import { useNotification } from '../context/NotificationContext';

const Notification = () => {
  const { notification } = useNotification();

  if (!notification) {
    return null;
  }

  return (
    <div className={`notification ${notification.type} ${notification ? 'show' : ''}`}>
      {notification.message}
    </div>
  );
};

export default Notification;