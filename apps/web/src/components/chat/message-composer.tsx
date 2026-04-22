"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";

interface MessageComposerProps {
  disabled: boolean;
  isSending: boolean;
  onSend: (text: string, files: File[]) => Promise<void>;
}

interface SelectedImage {
  file: File;
  previewUrl: string;
}

const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_FILES = 4;
const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;

export function MessageComposer({ disabled, isSending, onSend }: MessageComposerProps) {
  const [text, setText] = useState("");
  const [images, setImages] = useState<SelectedImage[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const imagesRef = useRef<SelectedImage[]>([]);

  const canSubmit = useMemo(() => {
    return Boolean(text.trim()) || images.length > 0;
  }, [images.length, text]);

  useEffect(() => {
    imagesRef.current = images;
  }, [images]);

  useEffect(() => {
    return () => {
      for (const image of imagesRef.current) {
        URL.revokeObjectURL(image.previewUrl);
      }
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    const currentText = text;
    const currentFiles = images.map((image) => image.file);
    for (const image of images) {
      URL.revokeObjectURL(image.previewUrl);
    }
    setText("");
    setImages([]);
    await onSend(currentText, currentFiles);
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? []);
    event.target.value = "";
    setFileError(null);

    if (selectedFiles.length === 0) {
      return;
    }

    const nextImages = [...images];
    for (const file of selectedFiles) {
      if (nextImages.length >= MAX_FILES) {
        setFileError(`Limite de ${MAX_FILES} imagens por mensagem.`);
        break;
      }
      if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
        setFileError("Formatos aceitos: JPG, PNG ou WebP.");
        continue;
      }
      if (file.size > MAX_FILE_SIZE_BYTES) {
        setFileError("Cada imagem deve ter ate 5 MB.");
        continue;
      }
      nextImages.push({
        file,
        previewUrl: URL.createObjectURL(file)
      });
    }

    setImages(nextImages);
  }

  function removeImage(index: number) {
    setImages((current) => {
      const image = current[index];
      if (image) {
        URL.revokeObjectURL(image.previewUrl);
      }
      return current.filter((_, currentIndex) => currentIndex !== index);
    });
  }

  return (
    <form className="border-t border-line bg-panel p-3" onSubmit={handleSubmit}>
      {images.length > 0 ? (
        <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {images.map((image, index) => (
            <div className="relative border border-line bg-surface" key={image.previewUrl}>
              <img
                alt={image.file.name}
                className="h-24 w-full object-cover"
                src={image.previewUrl}
              />
              <button
                className="absolute right-1 top-1 border border-line bg-panel px-2 py-1 text-xs text-ink"
                disabled={disabled || isSending}
                onClick={() => removeImage(index)}
                type="button"
              >
                Remover
              </button>
              <p className="truncate px-2 py-1 text-xs text-muted">{image.file.name}</p>
            </div>
          ))}
        </div>
      ) : null}

      {fileError ? (
        <p className="mb-2 text-sm text-danger">{fileError}</p>
      ) : null}

      <div className="flex items-end gap-2">
        <input
          accept={ACCEPTED_IMAGE_TYPES.join(",")}
          className="hidden"
          disabled={disabled || isSending}
          multiple
          onChange={handleFileChange}
          ref={fileInputRef}
          type="file"
        />
        <button
          className="h-12 border border-line px-3 text-sm font-medium text-ink disabled:bg-surface disabled:text-muted"
          disabled={disabled || isSending}
          onClick={() => fileInputRef.current?.click()}
          type="button"
        >
          Anexar
        </button>
        <textarea
          className="min-h-12 flex-1 resize-none border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-action"
          disabled={disabled || isSending}
          placeholder={disabled ? "Crie uma conversa para enviar mensagens" : "Digite sua mensagem"}
          rows={2}
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <button
          className="h-12 border border-action bg-action px-4 text-sm font-medium text-white disabled:border-line disabled:bg-surface disabled:text-muted"
          disabled={disabled || isSending || !canSubmit}
          type="submit"
        >
          {isSending ? "Enviando" : "Enviar"}
        </button>
      </div>
    </form>
  );
}
