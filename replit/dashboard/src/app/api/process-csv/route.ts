import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get('file') as File

    if (!file) {
      return NextResponse.json({ error: 'No file provided' }, { status: 400 })
    }

    if (!file.name.endsWith('.csv') && file.type !== 'text/csv') {
      return NextResponse.json({ error: 'File must be a CSV' }, { status: 400 })
    }

    const bytes = await file.arrayBuffer()
    const buffer = Buffer.from(bytes)

    console.log(`Received CSV: ${file.name}, Size: ${buffer.length} bytes`)

    return NextResponse.json({
      message: 'CSV received successfully',
      filename: file.name,
      size: buffer.length,
    })
  } catch (error) {
    console.error('Error handling CSV upload:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
