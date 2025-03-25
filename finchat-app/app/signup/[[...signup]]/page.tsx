import { SignUp } from "@clerk/nextjs"

export default function SignUpPage() {
  return (
    <div 
      className="flex justify-center items-center h-screen bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: "url('/images/bgimage.jpg')" }}
    >
      <SignUp forceRedirectUrl="/chat"/>
    </div>
  )
} 