import { useMutation } from '@tanstack/react-query';
import { sendMessage } from '@/shared/api';
import type { ChatRequest } from '@/shared/api/chat';

export function useSendMessage() {
  return useMutation({
    mutationFn: (req: ChatRequest) => sendMessage(req),
  });
}
