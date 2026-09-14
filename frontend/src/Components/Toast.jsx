import {toast} from 'react-toastify';

export const handleError=(msg)=>{
  toast.error(msg)
}

export const handleSuccess=(msg)=>{
  toast.success(msg);
}
