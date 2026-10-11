import Editor, { loader } from '@monaco-editor/react'
import * as monaco from 'monaco-editor/editor/editor.api'
import 'monaco-editor/languages/definitions/python/register'
import EditorWorker from 'monaco-editor/editor/editor.worker?worker'
import { useEffect, useState } from 'react'

// Загружаем редактор и worker из собственной сборки, без внешнего CDN.
self.MonacoEnvironment = { getWorker: () => new EditorWorker() }
loader.config({ monaco })

export default function CodeEditor(props) {
    const [mobile, setMobile] = useState(() => window.matchMedia('(max-width: 639px)').matches)
    useEffect(() => {
        const query = window.matchMedia('(max-width: 639px)')
        const update = () => setMobile(query.matches)
        query.addEventListener('change', update)
        return () => query.removeEventListener('change', update)
    }, [])
    return <Editor {...props} options={{
        ...props.options,
        automaticLayout: true,
        lineNumbers: 'on',
        lineNumbersMinChars: 2,
        glyphMargin: false,
        folding: !mobile,
        lineDecorationsWidth: mobile ? 4 : 10,
        minimap: { enabled: false },
        fontSize: mobile ? 16 : (props.options?.fontSize || 14),
        wordWrap: 'on',
        scrollBeyondLastLine: false,
        renderWhitespace: 'boundary',
        guides: { indentation: true },
        padding: { top: 12, bottom: 12 },
        quickSuggestions: !mobile,
        scrollbar: { verticalScrollbarSize: mobile ? 6 : 10 },
    }} />
}
